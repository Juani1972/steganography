"""
Stegstr Steganography Engine v2.2.0

5 modes: FORTRESS, ARMOR, GHOST, PHANTOM, HYBRID
Crypto: AES-256-GCM + Argon2id
ECC: Reed-Solomon
Sync: DCT corner markers (FORTRESS only)
"""

import numpy as np
from PIL import Image
import struct, hashlib, zlib, os, time
from typing import Optional, Tuple, Dict, List
from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)

MAX_PAYLOAD_BYTES = 10 * 1024 * 1024
MAX_MESSAGE_BYTES = 50 * 1024 * 1024
MAX_IMAGE_DIMENSION = 16384
MAX_ZLIB_RATIO = 100
MIN_DELTA = 0.5
MAX_DELTA = 100.0
MAX_EXTRACT_ITERATIONS = 30
SUPPORTED_VERSIONS = {2, 3}
VALID_ECC_VALUES = {0, 16, 24, 32, 40, 48, 64, 96}

class StegoMode(Enum):
    FORTRESS = auto()
    ARMOR = auto()
    GHOST = auto()
    PHANTOM = auto()
    HYBRID = auto()

class StegoEngine:
    PLATFORM_PROFILES = {
        "whatsapp_standard": {"max_dim": 1600, "qf": 55, "resize": True, "format": "jpeg", "ecc": 96},
        "whatsapp_hd": {"max_dim": 5120, "qf": 75, "resize": False, "format": "jpeg", "ecc": 48},
        "telegram_photo": {"max_dim": 2560, "qf": 82, "resize": False, "format": "jpeg", "ecc": 40},
        "telegram_file": {"max_dim": None, "qf": None, "resize": False, "format": "original", "ecc": 0},
        "instagram": {"max_dim": 1080, "qf": 75, "resize": True, "format": "jpeg", "ecc": 96},
        "twitter": {"max_dim": 4096, "qf": 85, "resize": False, "format": "jpeg", "ecc": 32},
        "facebook": {"max_dim": 2048, "qf": 80, "resize": False, "format": "jpeg", "ecc": 40},
        "signal": {"max_dim": 4096, "qf": 95, "resize": False, "format": "jpeg", "ecc": 16},
        "linkedin": {"max_dim": 7680, "qf": 85, "resize": False, "format": "jpeg", "ecc": 32},
        "reddit": {"max_dim": 8192, "qf": 90, "resize": False, "format": "jpeg", "ecc": 24},
    }

    SYNC_PATTERN = np.array([
        [1,0,1,1,0,1,0,0],
        [0,1,0,0,1,0,1,1],
        [1,0,0,1,1,0,0,1],
        [1,1,0,0,0,1,1,0],
        [0,0,1,1,0,0,1,1],
        [1,0,1,0,1,1,0,0],
        [0,1,0,1,0,0,1,1],
        [1,1,0,0,1,1,0,0],
    ], dtype=np.float32)

    def __init__(self, mode: StegoMode = StegoMode.HYBRID,
                 password: Optional[str] = None,
                 delta_override: Optional[float] = None,
                 ecc_override: Optional[int] = None):
        self.mode = mode
        self.password = password
        self.delta_override = self._validate_delta(delta_override)
        if ecc_override is not None and ecc_override not in VALID_ECC_VALUES:
            raise ValueError(f"Invalid ecc_override: {ecc_override}")
        self.ecc_override = ecc_override

    @staticmethod
    def _validate_delta(delta: Optional[float]) -> Optional[float]:
        if delta is None:
            return None
        delta = float(delta)
        if delta < MIN_DELTA or delta > MAX_DELTA:
            raise ValueError(f"delta_override must be between {MIN_DELTA} and {MAX_DELTA}, got {delta}")
        return delta

    @staticmethod
    def _safe_zlib_decompress(data: bytes, max_size: int = MAX_MESSAGE_BYTES) -> bytes:
        """Decompress with zip-bomb protection."""
        decompressor = zlib.decompressobj()
        buf = decompressor.decompress(data, max_size)
        if len(buf) >= max_size:
            raise ValueError("Potential zip bomb: decompressed data exceeds maximum allowed size")
        if decompressor.unconsumed_tail:
            raise ValueError("Potential zip bomb: compressed data exceeds maximum allowed size")
        return buf

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        try:
            from argon2.low_level import hash_secret_raw, Type
        except ImportError:
            raise RuntimeError("argon2-cffi is required. Install: pip install argon2-cffi")
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID,
        )

    def _encrypt(self, data: bytes) -> bytes:
        if not self.password:
            return data
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise RuntimeError("cryptography is required. Install: pip install cryptography")
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._derive_key(self.password, salt)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return salt + nonce + ciphertext

    def _decrypt(self, data: bytes) -> bytes:
        if not self.password:
            return data
        if len(data) < 28:
            raise ValueError("Ciphertext too short")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise RuntimeError("cryptography is required. Install: pip install cryptography")
        salt, nonce, ciphertext = data[:16], data[16:28], data[28:]
        key = self._derive_key(self.password, salt)
        return AESGCM(key).decrypt(nonce, ciphertext, None)

    @staticmethod
    def _dct2(block):
        from scipy.fftpack import dct
        return dct(dct(block.T, norm="ortho").T, norm="ortho")

    @staticmethod
    def _idct2(block):
        from scipy.fftpack import idct
        return idct(idct(block.T, norm="ortho").T, norm="ortho")

    @staticmethod
    def _watson_mask(dct_blocks):
        dc_vals = dct_blocks[:, :, 0, 0]
        dc_mean = np.mean(dc_vals)
        lum_mask = np.clip(np.abs(dc_vals - dc_mean) / (dc_mean + 1e-10), 0.1, 2.0)
        ac_energy = np.sqrt(np.sum(dct_blocks[:, :, 1:, 1:] ** 2, axis=(2, 3)) + 1e-10)
        texture_mask = np.clip(np.log1p(ac_energy / (np.mean(ac_energy) + 1e-10)), 0.5, 3.0)
        base = 2.0 * lum_mask[:, :, None, None] * texture_mask[:, :, None, None]
        fw = np.ones((8, 8))
        for i in range(8):
            for j in range(8):
                fw[i, j] = 1.0 + 0.1 * (i + j)
        return base * fw[None, None, :, :]

    @staticmethod
    def _rs_encode(data: bytes, ecc_bytes: int = 32) -> bytes:
        try:
            from reedsolo import RSCodec
            return RSCodec(nsym=ecc_bytes, nsize=255).encode(data)
        except ImportError:
            raise RuntimeError("reedsolo is required for ECC. Install: pip install reedsolo")

    @staticmethod
    def _rs_decode(data: bytes, ecc_bytes: int = 32) -> Optional[bytes]:
        try:
            from reedsolo import RSCodec
            return RSCodec(nsym=ecc_bytes, nsize=255).decode(data)[0]
        except Exception as e:
            logger.debug(f"RS decode failed: {e}")
            return None

    def _embed_sync_markers(self, image: np.ndarray, strength: float = 40.0) -> np.ndarray:
        result = image.copy()
        h, w = result.shape
        ms = 8
        corners = [(0, 0), (0, w - ms), (h - ms, 0), (h - ms, w - ms)]
        for (cy, cx) in corners:
            block = result[cy:cy+ms, cx:cx+ms].astype(np.float32)
            dct_block = self._dct2(block)
            dct_block[1:3, 1:3] += strength * self.SYNC_PATTERN[1:3, 1:3]
            result[cy:cy+ms, cx:cx+ms] = np.clip(self._idct2(dct_block), 0, 255)
        return result

    def _detect_sync_markers(self, image: np.ndarray, strength: float = 40.0) -> Tuple[bool, float]:
        h, w = image.shape
        ms = 8
        corners = [(0, 0), (0, w - ms), (h - ms, 0), (h - ms, w - ms)]
        corrs = []
        for (cy, cx) in corners:
            block = image[cy:cy+ms, cx:cx+ms].astype(np.float32)
            dct_block = self._dct2(block)
            extracted = dct_block[1:3, 1:3] / strength
            corr = np.corrcoef(extracted.flatten(), self.SYNC_PATTERN[1:3, 1:3].flatten())[0, 1]
            if not np.isnan(corr):
                corrs.append(corr)
        if not corrs:
            return False, 1.0
        avg = np.mean(corrs)
        return avg > 0.15, avg

    def _fortress_embed(self, image: np.ndarray, message_bits: np.ndarray, delta: float = 8.0) -> np.ndarray:
        h, w = image.shape
        h_blocks, w_blocks = h // 8, w // 8
        blocks = np.zeros((h_blocks, w_blocks, 8, 8))
        for i in range(h_blocks):
            for j in range(w_blocks):
                blocks[i, j] = image[i*8:(i+1)*8, j*8:(j+1)*8]
        dct_blocks = np.zeros_like(blocks)
        for i in range(h_blocks):
            for j in range(w_blocks):
                dct_blocks[i, j] = self._dct2(blocks[i, j])
        dc_coeffs = dct_blocks[:, :, 0, 0].copy()
        sb_h, sb_w = h_blocks // 2, w_blocks // 2
        capacity = sb_h * sb_w
        if len(message_bits) > capacity:
            raise ValueError(f"FORTRESS capacity exceeded: {len(message_bits)} > {capacity}")
        for idx in range(len(message_bits)):
            sb_i = idx // sb_w
            sb_j = idx % sb_w
            dc_window = dc_coeffs[sb_i*2:(sb_i+1)*2, sb_j*2:(sb_j+1)*2]
            dc_avg = np.mean(dc_window)
            bit = message_bits[idx]
            q = int(np.round(dc_avg / delta))
            if bit == 1:
                if q % 2 == 0: q += 1
            else:
                if q % 2 == 1: q += 1
            target_avg = q * delta
            diff = target_avg - dc_avg
            for di in range(2):
                for dj in range(2):
                    dc_coeffs[sb_i*2+di, sb_j*2+dj] += diff
        dct_blocks[:, :, 0, 0] = dc_coeffs
        result = np.zeros_like(image)
        for i in range(h_blocks):
            for j in range(w_blocks):
                result[i*8:(i+1)*8, j*8:(j+1)*8] = self._idct2(dct_blocks[i, j])
        return np.clip(result, 0, 255).astype(np.uint8)

    def _fortress_extract(self, image: np.ndarray, msg_len: int, delta: float = 8.0) -> Optional[np.ndarray]:
        h, w = image.shape
        h_blocks, w_blocks = h // 8, w // 8
        sb_h, sb_w = h_blocks // 2, w_blocks // 2
        capacity = sb_h * sb_w
        if msg_len > capacity:
            msg_len = capacity
        blocks = np.zeros((h_blocks, w_blocks, 8, 8))
        for i in range(h_blocks):
            for j in range(w_blocks):
                blocks[i, j] = image[i*8:(i+1)*8, j*8:(j+1)*8]
        dct_blocks = np.zeros_like(blocks)
        for i in range(h_blocks):
            for j in range(w_blocks):
                dct_blocks[i, j] = self._dct2(blocks[i, j])
        dc_coeffs = dct_blocks[:, :, 0, 0]
        bits = []
        for idx in range(msg_len):
            sb_i = idx // sb_w
            sb_j = idx % sb_w
            dc_window = dc_coeffs[sb_i*2:(sb_i+1)*2, sb_j*2:(sb_j+1)*2]
            dc_avg = np.mean(dc_window)
            q = int(np.round(dc_avg / delta))
            bits.append(q % 2)
        return np.array(bits, dtype=np.uint8)

    def _armor_embed(self, image: np.ndarray, message_bits: np.ndarray, delta: float = 4.0) -> np.ndarray:
        h, w = image.shape
        h_blocks, w_blocks = h // 8, w // 8
        zigzag = [(0,0),(0,1),(1,0),(2,0),(1,1),(0,2),(0,3),(1,2),(2,1),(3,0),(4,0),(3,1),(2,2),(1,3),(0,4),(0,5)]
        embed_positions = zigzag[1:6]
        capacity = h_blocks * w_blocks * len(embed_positions)
        if len(message_bits) > capacity:
            raise ValueError(f"ARMOR capacity exceeded: {len(message_bits)} > {capacity}")
        blocks = np.zeros((h_blocks, w_blocks, 8, 8))
        for i in range(h_blocks):
            for j in range(w_blocks):
                blocks[i, j] = image[i*8:(i+1)*8, j*8:(j+1)*8]
        dct_blocks = np.zeros_like(blocks)
        for i in range(h_blocks):
            for j in range(w_blocks):
                dct_blocks[i, j] = self._dct2(blocks[i, j])
        bit_idx = 0
        for i in range(h_blocks):
            for j in range(w_blocks):
                for pos in embed_positions:
                    if bit_idx >= len(message_bits):
                        break
                    ci, cj = pos
                    coeff = dct_blocks[i, j, ci, cj]
                    bit = message_bits[bit_idx]
                    q = int(np.round(coeff / delta))
                    if bit == 1:
                        if q % 2 == 0: q += 1
                    else:
                        if q % 2 == 1: q += 1
                    dct_blocks[i, j, ci, cj] = q * delta
                    bit_idx += 1
        result = np.zeros_like(image)
        for i in range(h_blocks):
            for j in range(w_blocks):
                result[i*8:(i+1)*8, j*8:(j+1)*8] = self._idct2(dct_blocks[i, j])
        return np.clip(result, 0, 255).astype(np.uint8)

    def _armor_extract(self, image: np.ndarray, msg_len: int, delta: float = 4.0) -> Optional[np.ndarray]:
        h, w = image.shape
        h_blocks, w_blocks = h // 8, w // 8
        zigzag = [(0,0),(0,1),(1,0),(2,0),(1,1),(0,2),(0,3),(1,2),(2,1),(3,0),(4,0),(3,1),(2,2),(1,3),(0,4),(0,5)]
        embed_positions = zigzag[1:6]
        capacity = h_blocks * w_blocks * len(embed_positions)
        if msg_len > capacity:
            msg_len = capacity
        blocks = np.zeros((h_blocks, w_blocks, 8, 8))
        for i in range(h_blocks):
            for j in range(w_blocks):
                blocks[i, j] = image[i*8:(i+1)*8, j*8:(j+1)*8]
        dct_blocks = np.zeros_like(blocks)
        for i in range(h_blocks):
            for j in range(w_blocks):
                dct_blocks[i, j] = self._dct2(blocks[i, j])
        bits = []
        bit_idx = 0
        for i in range(h_blocks):
            for j in range(w_blocks):
                for pos in embed_positions:
                    if bit_idx >= msg_len:
                        break
                    ci, cj = pos
                    coeff = dct_blocks[i, j, ci, cj]
                    q = int(np.round(coeff / delta))
                    bits.append(q % 2)
                    bit_idx += 1
        return np.array(bits, dtype=np.uint8)

    def _ghost_embed(self, image: np.ndarray, message_bits: np.ndarray) -> np.ndarray:
        flat = image.flatten().astype(np.uint8)
        if len(message_bits) > len(flat):
            raise ValueError(f"GHOST capacity exceeded: {len(message_bits)} > {len(flat)}")
        for i in range(len(message_bits)):
            flat[i] = (flat[i] & 0xFE) | int(message_bits[i])
        return flat.reshape(image.shape)

    def _ghost_extract(self, image: np.ndarray, msg_len: int) -> np.ndarray:
        flat = image.flatten().astype(np.uint8)
        return (flat[:msg_len] & 1).astype(np.uint8)

    def _phantom_embed(self, image: np.ndarray, message_bits: np.ndarray) -> np.ndarray:
        flat = image.flatten().astype(np.int16)
        if len(message_bits) > len(flat):
            raise ValueError(f"PHANTOM capacity exceeded: {len(message_bits)} > {len(flat)}")
        msg_hash = hashlib.sha256(message_bits.tobytes()).digest()
        seed = int.from_bytes(msg_hash[:4], "little")
        rng = np.random.default_rng(seed=seed)
        for i in range(len(message_bits)):
            lsb = flat[i] & 1
            target = int(message_bits[i])
            if lsb != target:
                if flat[i] == 0:
                    flat[i] += 1
                elif flat[i] == 255:
                    flat[i] -= 1
                else:
                    flat[i] += 1 if rng.random() > 0.5 else -1
        return np.clip(flat, 0, 255).astype(np.uint8).reshape(image.shape)

    def _phantom_extract(self, image: np.ndarray, msg_len: int) -> np.ndarray:
        flat = image.flatten().astype(np.uint8)
        return (flat[:msg_len] & 1).astype(np.uint8)

    def _bits_to_bytes(self, bits: np.ndarray) -> bytes:
        padding = (8 - len(bits) % 8) % 8
        if padding > 0:
            bits = np.concatenate([bits, np.zeros(padding, dtype=np.uint8)])
        out = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | int(bits[i + j])
            out.append(byte)
        return bytes(out)

    def _bytes_to_bits(self, data: bytes) -> np.ndarray:
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return np.array(bits, dtype=np.uint8)

    def _pack_message(self, data: bytes, mode: StegoMode,
                      platform: Optional[str] = None,
                      ecc_bytes: Optional[int] = None) -> Tuple[bytes, int]:
        MAGIC = b"STG\x00"
        VERSION = 3

        if len(data) > MAX_MESSAGE_BYTES:
            raise ValueError(f"Message too large: {len(data)} bytes")

        compressed = zlib.compress(data, level=9)
        payload = self._encrypt(compressed)

        if len(payload) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"Payload too large: {len(payload)} bytes")

        if ecc_bytes is not None:
            if ecc_bytes not in VALID_ECC_VALUES:
                raise ValueError(f"Invalid ecc_bytes: {ecc_bytes}")
        elif platform and platform in self.PLATFORM_PROFILES:
            ecc_bytes = self.PLATFORM_PROFILES[platform].get("ecc", 32)
        elif mode == StegoMode.FORTRESS:
            ecc_bytes = 96
        elif mode == StegoMode.ARMOR:
            ecc_bytes = 48
        else:
            ecc_bytes = 0

        if ecc_bytes > 0:
            payload = self._rs_encode(payload, ecc_bytes)

        header = struct.pack("<4sBBII", MAGIC, VERSION, mode.value, len(payload), ecc_bytes)
        packed = header + payload
        return packed, len(packed) * 8

    def _unpack_message(self, data: bytes, expected_mode: StegoMode) -> Optional[bytes]:
        if len(data) < 14:
            return None
        try:
            magic, version, mode_val, payload_len, ecc_bytes = struct.unpack("<4sBBII", data[:14])

            if magic != b"STG\x00":
                logger.debug(f"MAGIC mismatch: got {magic!r}")
                return None
            if version not in SUPPORTED_VERSIONS:
                logger.debug(f"Unsupported version: {version}")
                return None
            if mode_val not in {m.value for m in StegoMode}:
                logger.debug(f"Invalid mode value: {mode_val}")
                return None
            if ecc_bytes not in VALID_ECC_VALUES:
                logger.debug(f"Invalid ECC value: {ecc_bytes}")
                return None
            if payload_len < 0 or payload_len > MAX_PAYLOAD_BYTES:
                logger.debug(f"Payload length out of bounds: {payload_len}")
                return None
            if 14 + payload_len > len(data):
                logger.debug(f"Payload length exceeds data: {payload_len} > {len(data) - 14}")
                return None

            payload = data[14:14+payload_len]
            if ecc_bytes > 0:
                payload = self._rs_decode(payload, ecc_bytes)
                if payload is None:
                    return None

            if version == 2:
                decompressed = self._safe_zlib_decompress(payload)
                return self._decrypt(decompressed)
            else:
                decrypted = self._decrypt(payload)
                return self._safe_zlib_decompress(decrypted)
        except Exception as e:
            logger.debug(f"Unpack failed: {e}")
            return None

    def _extract_bits(self, y_arr: np.ndarray, msg_len: int, mode: StegoMode, delta: float) -> Optional[np.ndarray]:
        if mode == StegoMode.FORTRESS:
            return self._fortress_extract(y_arr, msg_len, delta)
        elif mode == StegoMode.ARMOR:
            return self._armor_extract(y_arr, msg_len, delta)
        elif mode == StegoMode.PHANTOM:
            return self._phantom_extract(y_arr, msg_len)
        else:
            return self._ghost_extract(y_arr, msg_len)

    @staticmethod
    def _check_path_security(path: str, allowed_base: Optional[str] = None) -> None:
        """Reject paths with traversal sequences or sensitive system targets."""
        from pathlib import Path
        p = Path(path).resolve()

        # FIX: Removed  from dangerous set because Windows 8.3 short names
        # (e.g. C:\Users\LAURAI~1\...) are legitimate and not an attack vector.
        dangerous = {"..", "$", "`", "|", ";", "&", "<", ">"}
        path_str = str(path)
        for d in dangerous:
            if d in path_str:
                raise ValueError(f"Path contains dangerous characters: {path}")

        if allowed_base is not None:
            base = Path(allowed_base).resolve()
            if not str(p).startswith(str(base)):
                raise ValueError(f"Path traversal detected: {path} is outside {allowed_base}")

        blocked_prefixes = ("/etc/", "/proc/", "/sys/", "/dev/", "/var/log/",
                            "C:/Windows", "C:/Program Files", "C:/System32")
        path_lower = str(p).lower()
        for prefix in blocked_prefixes:
            if path_lower.startswith(prefix.lower()):
                raise ValueError(f"Access to system path denied: {path}")

    def embed(self, cover_path: str, message: str or bytes, output_path: str,
              mode: Optional[StegoMode] = None, target_platform: Optional[str] = None,
              delta_override: Optional[float] = None,
              ecc_override: Optional[int] = None) -> Dict:
        self._check_path_security(cover_path)
        self._check_path_security(output_path)

        if not os.path.exists(cover_path):
            raise FileNotFoundError(f"Cover image not found: {cover_path}")

        img = Image.open(cover_path)
        if img.mode in ("RGBA", "P", "LA", "L"):
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert("RGB")

        w_img, h_img = img.size
        if w_img > MAX_IMAGE_DIMENSION or h_img > MAX_IMAGE_DIMENSION:
            raise ValueError(f"Image too large: {w_img}x{h_img}")

        MIN_DIMENSION = 64
        if w_img < MIN_DIMENSION or h_img < MIN_DIMENSION:
            raise ValueError(f"Cover too small ({w_img}x{h_img}). Min: {MIN_DIMENSION}x{MIN_DIMENSION}")

        if isinstance(message, str):
            message = message.encode("utf-8")
        if len(message) == 0:
            raise ValueError("Message cannot be empty")
        if len(message) > MAX_MESSAGE_BYTES:
            raise ValueError(f"Message too large: {len(message)} bytes")

        if mode is None:
            if self.mode != StegoMode.HYBRID:
                mode = self.mode
            else:
                mode = self._auto_select_mode(target_platform, len(message))

        if target_platform and target_platform in self.PLATFORM_PROFILES:
            profile = self.PLATFORM_PROFILES[target_platform]
            if profile["resize"] and profile["max_dim"]:
                img = self._pre_size_image(img, profile["max_dim"])

        w, h = img.size
        w = (w // 8) * 8
        h = (h // 8) * 8
        img = img.crop((0, 0, w, h))

        effective_ecc = ecc_override if ecc_override is not None else self.ecc_override
        packed, bit_len = self._pack_message(message, mode, target_platform, ecc_bytes=effective_ecc)
        message_bits = self._bytes_to_bits(packed)

        effective_delta = self._validate_delta(
            delta_override if delta_override is not None else self.delta_override
        )

        if mode in (StegoMode.GHOST, StegoMode.PHANTOM):
            rgb_arr = np.array(img, dtype=np.uint8)
            if mode == StegoMode.GHOST:
                embedded_arr = self._ghost_embed(rgb_arr, message_bits)
            else:
                embedded_arr = self._phantom_embed(rgb_arr, message_bits)
            result = Image.fromarray(embedded_arr, mode="RGB")
            result.save(output_path, "PNG", optimize=True)
            output_format = "PNG"
            quality_metrics = {}
        else:
            img_ycbcr = img.convert("YCbCr")
            y, cb, cr = img_ycbcr.split()
            y_arr = np.array(y, dtype=np.float32)

            if mode == StegoMode.FORTRESS:
                y_embedded = self._fortress_embed(y_arr, message_bits, delta=effective_delta if effective_delta else 24.0)
            elif mode == StegoMode.ARMOR:
                y_embedded = self._armor_embed(y_arr, message_bits, delta=effective_delta if effective_delta else 16.0)
            else:
                try:
                    y_embedded = self._fortress_embed(y_arr, message_bits, delta=effective_delta if effective_delta else 24.0)
                    mode = StegoMode.FORTRESS
                except ValueError:
                    y_embedded = self._armor_embed(y_arr, message_bits, delta=effective_delta if effective_delta else 16.0)
                    mode = StegoMode.ARMOR

            if mode == StegoMode.FORTRESS:
                y_embedded = self._embed_sync_markers(y_embedded)

            quality_metrics = {}
            try:
                orig_y = y_arr.astype(np.float32)
                stego_y = y_embedded.astype(np.float32)
                mse = np.mean((orig_y - stego_y) ** 2)
                psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float("inf")
                quality_metrics = {
                    "mse": round(float(mse), 4),
                    "psnr_db": round(float(psnr), 2),
                    "ssim": round(self._compute_ssim(orig_y, stego_y), 4),
                }
            except Exception:
                pass

            y_img = Image.fromarray(y_embedded.astype(np.uint8), mode="L")
            cb_img = cb.resize((w, h), Image.LANCZOS)
            cr_img = cr.resize((w, h), Image.LANCZOS)
            merged = Image.merge("YCbCr", (y_img, cb_img, cr_img))
            result = merged.convert("RGB")

            ext = os.path.splitext(output_path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                qf = 85
                if target_platform and target_platform in self.PLATFORM_PROFILES:
                    qf = self.PLATFORM_PROFILES[target_platform].get("qf", 85)
                result.save(output_path, "JPEG", quality=qf, optimize=True)
                output_format = "JPEG"
            else:
                result.save(output_path, "PNG", optimize=True)
                output_format = "PNG"

        delta_used = effective_delta if effective_delta else (24.0 if mode == StegoMode.FORTRESS else (16.0 if mode == StegoMode.ARMOR else 0.0))
        ecc_used = effective_ecc if effective_ecc is not None else (
            self.PLATFORM_PROFILES.get(target_platform, {}).get("ecc", 0) if target_platform else (
                96 if mode == StegoMode.FORTRESS else (48 if mode == StegoMode.ARMOR else 0)
            )
        )

        return {
            "mode": mode.name,
            "platform": target_platform,
            "capacity_bits": len(message_bits),
            "message_bytes": len(message),
            "image_size": result.size,
            "output_format": output_format,
            "delta_used": delta_used,
            "ecc_used": ecc_used,
            "quality_metrics": quality_metrics,
            "status": "success",
        }

    def extract(self, stego_path: str, expected_mode: Optional[StegoMode] = None) -> Optional[Dict]:
        self._check_path_security(stego_path)

        if not os.path.exists(stego_path):
            raise FileNotFoundError(f"Stego image not found: {stego_path}")

        img = Image.open(stego_path)
        if img.mode in ("RGBA", "P", "LA", "L"):
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert("RGB")

        rgb_arr = np.array(img, dtype=np.uint8)
        img_ycbcr = img.convert("YCbCr")
        y, _, _ = img_ycbcr.split()
        y_arr = np.array(y, dtype=np.float32)

        modes_to_try = [expected_mode] if expected_mode else [StegoMode.FORTRESS, StegoMode.ARMOR, StegoMode.PHANTOM, StegoMode.GHOST]
        iteration_count = 0

        for mode in modes_to_try:
            if mode is None:
                continue
            if mode == StegoMode.FORTRESS:
                base_delta = getattr(self, "delta_override", None) or 24.0
                deltas = [base_delta, 2.0, 2.5, 3.5, 4.0, 5.0, 6.0, 7.0, 10.0, 15.0]
            elif mode == StegoMode.ARMOR:
                base_delta = getattr(self, "delta_override", None) or 16.0
                deltas = [base_delta, 2.0, 2.5, 3.5, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0]
            else:
                deltas = [0.0]

            seen = set()
            unique_deltas = []
            for d in deltas:
                if d not in seen:
                    seen.add(d)
                    unique_deltas.append(d)
            deltas = unique_deltas

            extract_arr = rgb_arr if mode in (StegoMode.GHOST, StegoMode.PHANTOM) else y_arr

            for delta in deltas:
                iteration_count += 1
                if iteration_count > MAX_EXTRACT_ITERATIONS:
                    logger.warning("Extraction iteration limit reached")
                    return None

                header_bits = 14 * 8
                bits = self._extract_bits(extract_arr, header_bits, mode, delta)
                if bits is None or len(bits) < header_bits:
                    continue
                header_data = self._bits_to_bytes(bits[:header_bits])
                try:
                    magic, version, mode_val, payload_len, ecc_bytes = struct.unpack("<4sBBII", header_data)
                    if magic != b"STG\x00":
                        continue
                    if version not in SUPPORTED_VERSIONS:
                        continue
                    if mode_val not in {m.value for m in StegoMode}:
                        continue
                    if payload_len > MAX_PAYLOAD_BYTES:
                        continue

                    total_bits = 14 * 8 + payload_len * 8
                    bits = self._extract_bits(extract_arr, total_bits, mode, delta)
                    full_data = self._bits_to_bytes(bits)
                    message = self._unpack_message(full_data, mode)
                    if message is not None:
                        decoded_message = None
                        encoding = "binary"
                        if isinstance(message, bytes):
                            try:
                                decoded_message = message.decode("utf-8")
                                encoding = "utf-8"
                            except UnicodeDecodeError:
                                import base64
                                decoded_message = base64.b64encode(message).decode("ascii")
                                encoding = "base64"
                        else:
                            decoded_message = message
                            encoding = "utf-8"

                        return {
                            "message": decoded_message,
                            "mode": mode.name,
                            "raw_bytes": len(message) if isinstance(message, bytes) else len(str(message).encode("utf-8")),
                            "delta_used": delta,
                            "encoding": encoding,
                        }
                except Exception as e:
                    logger.debug(f"Extraction failed for {mode} delta={delta}: {e}")
                    continue
        return None

    def _auto_select_mode(self, target_platform: Optional[str], msg_len: int) -> StegoMode:
        if target_platform is None:
            return StegoMode.ARMOR
        profile = self.PLATFORM_PROFILES.get(target_platform, {})
        if profile.get("resize") or profile.get("qf", 100) < 65:
            return StegoMode.FORTRESS
        elif profile.get("qf", 100) < 85:
            return StegoMode.ARMOR
        else:
            return StegoMode.PHANTOM

    def _pre_size_image(self, img: Image.Image, max_dim: int) -> Image.Image:
        w, h = img.size
        max_current = max(w, h)
        if max_current > max_dim:
            scale = max_dim / max_current
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return img

    @staticmethod
    def _compute_ssim(img1: np.ndarray, img2: np.ndarray, window_size: int = 11) -> float:
        try:
            from skimage.metrics import structural_similarity as ssim
            return ssim(img1, img2, data_range=255.0)
        except ImportError:
            c1 = (0.01 * 255) ** 2
            c2 = (0.03 * 255) ** 2
            mu1 = np.mean(img1)
            mu2 = np.mean(img2)
            sigma1_sq = np.var(img1)
            sigma2_sq = np.var(img2)
            sigma12 = np.mean((img1 - mu1) * (img2 - mu2))
            ssim_val = ((2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)) / ((mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2))
            return float(ssim_val)

    def get_capacity(self, image_path: str, mode: StegoMode,
                     platform: Optional[str] = None,
                     ecc_bytes: Optional[int] = None) -> int:
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        w = (w // 8) * 8
        h = (h // 8) * 8
        h_blocks, w_blocks = h // 8, w // 8
        if mode == StegoMode.FORTRESS:
            sb_h, sb_w = h_blocks // 2, w_blocks // 2
            bits = sb_h * sb_w
        elif mode == StegoMode.ARMOR:
            bits = h_blocks * w_blocks * 5
        elif mode == StegoMode.PHANTOM:
            bits = w * h
        else:
            bits = w * h

        if ecc_bytes is None:
            if platform and platform in self.PLATFORM_PROFILES:
                ecc_bytes = self.PLATFORM_PROFILES[platform].get("ecc", 0)
            elif mode == StegoMode.FORTRESS:
                ecc_bytes = 96
            elif mode == StegoMode.ARMOR:
                ecc_bytes = 48
            else:
                ecc_bytes = 0
        else:
            if ecc_bytes not in VALID_ECC_VALUES:
                raise ValueError(f"Invalid ecc_bytes: {ecc_bytes}")

        overhead = 14 * 8 + ecc_bytes * 8
        return max(0, bits - overhead) // 8

    def auto_tune(self, cover_path: str, message: str or bytes, target_platform: str,
                  search_depth: str = "standard") -> Dict:
        import tempfile, shutil
        from stegstr.platform.simulator import PlatformSimulator

        msg_str = message.decode("utf-8") if isinstance(message, bytes) else message
        tmpdir = tempfile.mkdtemp()
        sim = PlatformSimulator()

        if target_platform in ["whatsapp_standard", "instagram"]:
            candidate_modes = [StegoMode.FORTRESS, StegoMode.ARMOR]
        elif target_platform in ["telegram_photo", "twitter", "facebook", "linkedin", "reddit"]:
            candidate_modes = [StegoMode.ARMOR, StegoMode.FORTRESS]
        elif target_platform in ["telegram_file", "signal"]:
            candidate_modes = [StegoMode.PHANTOM, StegoMode.ARMOR]
        else:
            candidate_modes = [StegoMode.ARMOR, StegoMode.FORTRESS, StegoMode.PHANTOM]

        if search_depth == "quick":
            delta_ranges = {
                StegoMode.FORTRESS: [4.0, 8.0, 12.0],
                StegoMode.ARMOR: [2.0, 4.0, 6.0],
                StegoMode.PHANTOM: [0.0],
            }
            ecc_levels = [0, 32, 64, 96]
        elif search_depth == "deep":
            delta_ranges = {
                StegoMode.FORTRESS: [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0],
                StegoMode.ARMOR: [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0],
                StegoMode.PHANTOM: [0.0],
            }
            ecc_levels = [0, 16, 24, 32, 40, 48, 64, 96]
        else:
            delta_ranges = {
                StegoMode.FORTRESS: [3.0, 5.0, 8.0, 10.0, 15.0],
                StegoMode.ARMOR: [2.0, 3.0, 4.0, 6.0, 8.0],
                StegoMode.PHANTOM: [0.0],
            }
            ecc_levels = [0, 16, 32, 48, 64, 96]

        coarse_results = []
        for mode in candidate_modes:
            for delta in delta_ranges[mode]:
                for ecc in ecc_levels:
                    if mode in (StegoMode.GHOST, StegoMode.PHANTOM) and ecc > 0:
                        continue
                    if mode == StegoMode.FORTRESS and ecc < 32:
                        continue
                    try:
                        stego_path = os.path.join(tmpdir, f"st_m{mode.value}_d{delta}_e{ecc}.png")
                        engine = StegoEngine(
                            mode=mode,
                            password=getattr(self, "password", None),
                            delta_override=delta,
                            ecc_override=ecc
                        )
                        meta = engine.embed(cover_path, message, stego_path,
                                            target_platform=target_platform,
                                            delta_override=delta,
                                            ecc_override=ecc)

                        processed_path = os.path.join(tmpdir, f"proc_m{mode.value}_d{delta}_e{ecc}.jpg")
                        sim.simulate(target_platform, stego_path, processed_path)

                        extracted = engine.extract(processed_path)
                        success = extracted is not None and extracted.get("message") == msg_str

                        psnr = meta.get("quality_metrics", {}).get("psnr_db", 30.0)
                        cap_bits = meta["capacity_bits"]
                        msg_bits = meta["message_bytes"] * 8
                        headroom = max(0, (cap_bits - msg_bits) / max(cap_bits, 1)) * 10

                        robustness_score = 100.0 if success else 0.0
                        quality_score = min(40.0, max(0.0, psnr - 30.0))
                        score = robustness_score + quality_score + headroom

                        coarse_results.append({
                            "mode": mode, "delta": delta, "ecc": ecc,
                            "success": success, "score": score, "psnr": psnr,
                            "meta": meta, "extracted": extracted,
                        })
                    except Exception as e:
                        logger.debug(f"Coarse search failed: {e}")
                        continue

        if not coarse_results:
            shutil.rmtree(tmpdir)
            # FIX: Added candidates_tested to avoid KeyError in tests
            return {"delta": 8.0, "mode": StegoMode.ARMOR, "ecc": 48, "success": False,
                    "score": 0, "meta": None, "extracted": None, "phase": "coarse_failed",
                    "candidates_tested": 0}

        coarse_results.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = coarse_results[:3]

        fine_results = []
        for candidate in top_candidates:
            base_delta = candidate["delta"]
            mode = candidate["mode"]
            ecc = candidate["ecc"]
            fine_deltas = [base_delta - 1.0, base_delta - 0.5, base_delta, base_delta + 0.5, base_delta + 1.0]
            fine_deltas = [max(MIN_DELTA, d) for d in fine_deltas]
            fine_deltas = sorted(list(set(fine_deltas)))

            for fd in fine_deltas:
                try:
                    stego_path = os.path.join(tmpdir, f"fine_m{mode.value}_d{fd}_e{ecc}.png")
                    engine = StegoEngine(
                        mode=mode,
                        password=getattr(self, "password", None),
                        delta_override=fd,
                        ecc_override=ecc
                    )
                    meta = engine.embed(cover_path, message, stego_path,
                                        target_platform=target_platform,
                                        delta_override=fd,
                                        ecc_override=ecc)
                    processed_path = os.path.join(tmpdir, f"fine_proc_m{mode.value}_d{fd}_e{ecc}.jpg")
                    sim.simulate(target_platform, stego_path, processed_path)
                    extracted = engine.extract(processed_path)
                    success = extracted is not None and extracted.get("message") == msg_str

                    psnr = meta.get("quality_metrics", {}).get("psnr_db", 30.0)
                    cap_bits = meta["capacity_bits"]
                    msg_bits = meta["message_bytes"] * 8
                    headroom = max(0, (cap_bits - msg_bits) / max(cap_bits, 1)) * 10

                    robustness_score = 100.0 if success else 0.0
                    quality_score = min(40.0, max(0.0, psnr - 30.0))
                    score = robustness_score + quality_score + headroom

                    fine_results.append({
                        "mode": mode, "delta": fd, "ecc": ecc,
                        "success": success, "score": score, "psnr": psnr,
                        "meta": meta, "extracted": extracted,
                    })
                except Exception as e:
                    logger.debug(f"Fine search failed: {e}")
                    continue

        all_results = coarse_results + fine_results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        successful = [r for r in all_results if r["success"]]
        best = successful[0] if successful else (all_results[0] if all_results else None)

        shutil.rmtree(tmpdir)
        if best is None:
            # FIX: Added candidates_tested to avoid KeyError in tests
            return {"delta": 8.0, "mode": StegoMode.ARMOR, "ecc": 48, "success": False,
                    "score": 0, "meta": None, "extracted": None, "phase": "no_candidates",
                    "candidates_tested": len(all_results)}

        return {
            "delta": best["delta"],
            "mode": best["mode"],
            "ecc": best["ecc"],
            "success": best["success"],
            "score": round(best["score"], 2),
            "psnr_db": round(best["psnr"], 2),
            "meta": best["meta"],
            "extracted": best["extracted"],
            "phase": "complete",
            "candidates_tested": len(all_results),
        }
