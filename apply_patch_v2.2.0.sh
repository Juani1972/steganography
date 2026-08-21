#!/bin/bash
# apply_patch_v2.2.0.sh
# Script para aplicar el parche de coherencia v2.2.0

echo "Aplicando parche Stegstr v2.2.0..."

if [ ! -d "stegstr/gui" ]; then
    echo "Error: No se encuentra el directorio stegstr/gui"
    echo "Ejecuta este script desde la raíz del repositorio"
    exit 1
fi

# Backup
cp stegstr/gui/widget.html stegstr/gui/widget.html.bak
cp stegstr/gui/widget_server.py stegstr/gui/widget_server.py.bak
cp stegstr/gui/web_app.py stegstr/gui/web_app.py.bak

echo "Backups creados: *.bak"

# Aplicar parche
cp patch/stegstr/gui/widget.html stegstr/gui/widget.html
cp patch/stegstr/gui/widget_server.py stegstr/gui/widget_server.py
cp patch/stegstr/gui/web_app.py stegstr/gui/web_app.py

echo "Parche aplicado correctamente."
echo ""
echo "Verifica los cambios con:"
echo "  diff stegstr/gui/widget.html.bak stegstr/gui/widget.html"
echo ""
echo "Luego commit:"
echo "  git add stegstr/gui/"
echo "  git commit -m 'v2.2.0: parche coherencia GUI-backend'"
echo "  git tag v2.2.0"
