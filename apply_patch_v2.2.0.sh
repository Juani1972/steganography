#!/bin/bash
# apply_patch_v2.2.0.sh
# Script para aplicar el parche de coherencia v2.2.0

PATCH_DIR="${1:-stegstr-v2.2.0-patch}"

echo "Aplicando parche Stegstr v2.2.0..."
echo "Buscando parche en: $PATCH_DIR"

if [ ! -d "$PATCH_DIR/stegstr/gui" ]; then
    echo "Error: No se encuentra el directorio $PATCH_DIR/stegstr/gui"
    echo ""
    echo "Uso correcto:"
    echo "  1. Descomprime el ZIP: unzip stegstr-v2.2.0-patch.zip"
    echo "  2. Desde la raíz del repositorio, ejecuta:"
    echo "     bash stegstr-v2.2.0-patch/apply_patch_v2.2.0.sh"
    exit 1
fi

if [ ! -d "stegstr/gui" ]; then
    echo "Error: No se encuentra stegstr/gui en el directorio actual"
    echo "Ejecuta este script desde la raíz del repositorio (donde está stegstr/)"
    exit 1
fi

# Backup
cp stegstr/gui/widget.html stegstr/gui/widget.html.bak
cp stegstr/gui/widget_server.py stegstr/gui/widget_server.py.bak
cp stegstr/gui/web_app.py stegstr/gui/web_app.py.bak

echo "Backups creados: *.bak"

# Aplicar parche
cp "$PATCH_DIR/stegstr/gui/widget.html" stegstr/gui/widget.html
cp "$PATCH_DIR/stegstr/gui/widget_server.py" stegstr/gui/widget_server.py
cp "$PATCH_DIR/stegstr/gui/web_app.py" stegstr/gui/web_app.py

# Actualizar requirements.txt si existe
if [ -f "$PATCH_DIR/requirements.txt" ]; then
    cp "$PATCH_DIR/requirements.txt" requirements.txt
    echo "requirements.txt actualizado"
fi

echo "Parche aplicado correctamente."
echo ""
echo "Verifica los cambios con:"
echo "  diff stegstr/gui/widget.html.bak stegstr/gui/widget.html"
echo "  diff stegstr/gui/widget_server.py.bak stegstr/gui/widget_server.py"
echo "  diff stegstr/gui/web_app.py.bak stegstr/gui/web_app.py"
echo ""
echo "Prueba de importación:"
echo "  python -c "from stegstr.gui.widget_server import app; print('widget_server OK')""
echo "  python -c "from stegstr.gui.web_app import app; print('web_app OK')""
echo ""
echo "Si todo está correcto, commitea y etiqueta:"
echo "  git add stegstr/gui/ requirements.txt"
echo "  git commit -m 'v2.2.0: parche coherencia GUI-backend + fixes de importación'"
echo "  git tag v2.2.0"
