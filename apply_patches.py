#!/usr/bin/env python3
"""
Stegstr v2.2.0 — Script de aplicación de correcciones

Aplica automáticamente todos los cambios de la auditoría:
  1. Sobreescribe archivos completos (README, pyproject.toml, wizard, etc.)
  2. Reemplaza versiones in-place en archivos grandes (engine, validate)
  3. Verifica que cada cambio se aplicó correctamente

Uso:
    python apply_patches.py

Requisitos: estar en la raíz del repositorio stegstr.
"""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(ROOT) if os.path.basename(ROOT) == "stegstr-v2.2.0-update" else ROOT

def check_repo():
    """Verify we are in the stegstr repository."""
    markers = ["stegstr", "pyproject.toml", "validate.py", "README.md"]
    found = sum(1 for m in markers if os.path.exists(os.path.join(REPO_ROOT, m)))
    if found < 3:
        print(f"❌ Error: No parece ser la raíz del repo stegstr.")
        print(f"   Se esperaban al menos 3 de: {markers}")
        print(f"   Directorio detectado: {REPO_ROOT}")
        sys.exit(1)
    print(f"✅ Repo detectado: {REPO_ROOT}")

def copy_file(src, dst, desc):
    """Copy src to dst with verification."""
    try:
        shutil.copy2(src, dst)
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            print(f"  ✅ {desc}")
            return True
        else:
            print(f"  ⚠️  {desc} — tamaño no coincide")
            return False
    except Exception as e:
        print(f"  ❌ {desc} — {e}")
        return False

def patch_file(filepath, old, new, desc, count=1):
    """Replace old with new in file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if old not in content:
            print(f"  ⚠️  {desc} — texto no encontrado (¿ya aplicado?)")
            return False
        content = content.replace(old, new, count)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ {desc}")
        return True
    except Exception as e:
        print(f"  ❌ {desc} — {e}")
        return False

def main():
    print("=" * 70)
    print(" Stegstr v2.2.0 — Aplicación de correcciones de auditoría")
    print("=" * 70)
    check_repo()

    ok = True

    # ── 1. Archivos raíz ──
    print("\n📄 Archivos raíz...")
    ok &= copy_file(
        os.path.join(ROOT, "README.md"),
        os.path.join(REPO_ROOT, "README.md"),
        "README.md reescrito"
    )
    ok &= copy_file(
        os.path.join(ROOT, "pyproject.toml"),
        os.path.join(REPO_ROOT, "pyproject.toml"),
        "pyproject.toml (scipy en base, v2.2.0)"
    )
    ok &= copy_file(
        os.path.join(ROOT, ".env.example"),
        os.path.join(REPO_ROOT, ".env.example"),
        ".env.example nuevo"
    )
    ok &= copy_file(
        os.path.join(ROOT, "validate.py"),
        os.path.join(REPO_ROOT, "validate.py"),
        "validate.py (v2.2.0)"
    )

    # ── 2. stegstr/ ──
    print("\n🔧 Módulos stegstr...")
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "stego", "engine.py"),
        os.path.join(REPO_ROOT, "stegstr", "stego", "engine.py"),
        "stegstr/stego/engine.py (v2.2.0)"
    )
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "config", "wizard.py"),
        os.path.join(REPO_ROOT, "stegstr", "config", "wizard.py"),
        "stegstr/config/wizard.py (credenciales sincronizadas)"
    )
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "api", "agent_api.py"),
        os.path.join(REPO_ROOT, "stegstr", "api", "agent_api.py"),
        "stegstr/api/agent_api.py (v2.2.0)"
    )
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "api", "server.py"),
        os.path.join(REPO_ROOT, "stegstr", "api", "server.py"),
        "stegstr/api/server.py (NotImplementedError)"
    )
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "video", "engine.py"),
        os.path.join(REPO_ROOT, "stegstr", "video", "engine.py"),
        "stegstr/video/engine.py (NotImplementedError)"
    )
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "gui", "widget.html"),
        os.path.join(REPO_ROOT, "stegstr", "gui", "widget.html"),
        "stegstr/gui/widget.html (SPA interactiva funcional)"
    )
    ok &= copy_file(
        os.path.join(ROOT, "stegstr", "gui", "widget_server.py"),
        os.path.join(REPO_ROOT, "stegstr", "gui", "widget_server.py"),
        "stegstr/gui/widget_server.py (servidor REST para el widget)"
    )

    # ── 3. scripts/ ──
    print("\n📜 Scripts...")
    ok &= copy_file(
        os.path.join(ROOT, "scripts", "health_check.py"),
        os.path.join(REPO_ROOT, "scripts", "health_check.py"),
        "scripts/health_check.py (v2.2.0, typer, scipy)"
    )

    # ── 4. Reemplazos in-place (por si acaso) ──
    print("\n🔍 Verificando reemplazos de versión...")
    patch_file(
        os.path.join(REPO_ROOT, "stegstr", "stego", "engine.py"),
        'Stegstr Steganography Engine v2.1.5',
        'Stegstr Steganography Engine v2.2.0',
        "engine.py docstring (fallback)"
    )
    patch_file(
        os.path.join(REPO_ROOT, "validate.py"),
        'Stegstr Exhaustive Validation Suite v2.1.5 — Fase 7.1 (Corregido)',
        'Stegstr Exhaustive Validation Suite v2.2.0',
        "validate.py docstring (fallback)",
        count=2
    )
    patch_file(
        os.path.join(REPO_ROOT, "scripts", "health_check.py"),
        'Stegstr v2.1.5 Health Check',
        'Stegstr v2.2.0 Health Check',
        "health_check.py print (fallback)"
    )
    patch_file(
        os.path.join(REPO_ROOT, "stegstr", "api", "agent_api.py"),
        'version="2.1.5"',
        'version="2.2.0"',
        "agent_api.py version (fallback)",
        count=2
    )
    patch_file(
        os.path.join(REPO_ROOT, "stegstr", "api", "agent_api.py"),
        '"version": "2.1.5"',
        '"version": "2.2.0"',
        "agent_api.py health version (fallback)"
    )

    # ── 5. Resumen ──
    print("\n" + "=" * 70)
    if ok:
        print("✅ Todas las correcciones aplicadas correctamente.")
    else:
        print("⚠️  Algunas correcciones tuvieron problemas. Revisa los mensajes arriba.")
    print("=" * 70)
    print("\nPróximos pasos:")
    print("  1. Reinstalar dependencias:  pip install -e '.[all]'")
    print("  2. Verificar:                 python validate.py")
    print("  3. Verificar:                 python check_env.py")
    print("  4. Verificar CLI:             python -m stegstr.cli --help")
    print("  5. Configurar credenciales:   python -m stegstr.cli config --wizard")
    print("  6. Iniciar widget:             python -m stegstr.gui.widget_server")
    print("  7. Abrir navegador:           http://127.0.0.1:8080")
    print("=" * 70)

if __name__ == "__main__":
    main()
