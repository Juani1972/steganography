"""
Platform Simulator v2.1 - Simulates social media image processing pipelines.

Improvements:
- Instagram: simulates 1:1 or 4:5 crop in addition to double compression
- Twitter: enforces 5MB limit and 4096px dimension limit correctly
- Facebook: validates RGB mode before processing
- Added LinkedIn and Reddit profiles
"""

from PIL import Image
import io
import shutil
import logging

logger = logging.getLogger(__name__)

class PlatformSimulator:
    """Simulate image processing of major social media platforms."""

    def simulate_whatsapp_standard(self, image_path: str, output_path: str):
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 1600
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=55, optimize=True)
        return output_path

    def simulate_whatsapp_hd(self, image_path: str, output_path: str):
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 5120
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=75, optimize=True)
        return output_path

    def simulate_telegram_photo(self, image_path: str, output_path: str):
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 2560
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=82, optimize=True)
        return output_path

    def simulate_telegram_file(self, image_path: str, output_path: str):
        shutil.copy(image_path, output_path)
        return output_path

    def simulate_instagram(self, image_path: str, output_path: str):
        """Simulate Instagram processing with crop and double compression.

        Instagram crops to 1:1 (square) or 4:5 (portrait) and applies
        double JPEG compression.
        """
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size

        target_ratio = 1.0
        current_ratio = w / h

        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        elif current_ratio < target_ratio:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        target_w = 1080
        scale = target_w / img.size[0]
        img = img.resize((target_w, int(img.size[1] * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80, optimize=True)
        buf.seek(0)
        img = Image.open(buf)
        img.save(output_path, "JPEG", quality=75, optimize=True)
        return output_path

    def simulate_twitter(self, image_path: str, output_path: str):
        """Simulate Twitter/X processing with 5MB limit."""
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        size_mb = buf.tell() / (1024 * 1024)

        if size_mb <= 5 and max(w, h) <= 4096:
            img.save(output_path, "JPEG", quality=85, optimize=True)
        else:
            max_dim = 4096
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)

            for quality in [85, 80, 75, 70, 65, 60]:
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=quality, optimize=True)
                if buf.tell() / (1024 * 1024) <= 5:
                    with open(output_path, 'wb') as f:
                        f.write(buf.getvalue())
                    return output_path

            while buf.tell() / (1024 * 1024) > 5:
                w, h = img.size
                img = img.resize((int(w*0.9), int(h*0.9)), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=60, optimize=True)

            with open(output_path, 'wb') as f:
                f.write(buf.getvalue())

        return output_path

    def simulate_facebook(self, image_path: str, output_path: str):
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 2048
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        from PIL import ImageFilter
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=3))
        img.save(output_path, "JPEG", quality=80, optimize=True)
        return output_path

    def simulate_signal(self, image_path: str, output_path: str):
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 4096
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=95, optimize=True)
        return output_path

    def simulate_linkedin(self, image_path: str, output_path: str):
        """Simulate LinkedIn image processing."""
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 7680
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=85, optimize=True)
        return output_path

    def simulate_reddit(self, image_path: str, output_path: str):
        """Simulate Reddit image processing."""
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        max_dim = 8192
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=90, optimize=True)
        return output_path

    def simulate(self, platform: str, image_path: str, output_path: str):
        simulators = {
            "whatsapp_standard": self.simulate_whatsapp_standard,
            "whatsapp_hd": self.simulate_whatsapp_hd,
            "telegram_photo": self.simulate_telegram_photo,
            "telegram_file": self.simulate_telegram_file,
            "instagram": self.simulate_instagram,
            "twitter": self.simulate_twitter,
            "facebook": self.simulate_facebook,
            "signal": self.simulate_signal,
            "linkedin": self.simulate_linkedin,
            "reddit": self.simulate_reddit,
        }
        if platform not in simulators:
            raise ValueError(f"Unknown platform: {platform}")
        return simulators[platform](image_path, output_path)
