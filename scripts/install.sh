#!/usr/bin/env bash
set -e

APP_DIR="$HOME/.local/share/imggone"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
SCRIPT_URL="https://raw.githubusercontent.com/JovanEhren/ImgGone/main/main.py"
UNINSTALL_URL="https://raw.githubusercontent.com/JovanEhren/ImgGone/main/scripts/uninstall.sh"

echo "Installing ImgGone..."

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

# Check PyQt6
if ! python3 -c "import PyQt6" &>/dev/null; then
    echo "Error: PyQt6 is required. Install it with your package manager:"
    echo "  Arch/CachyOS: sudo pacman -S python-pyqt6"
    echo "  Debian/Ubuntu: sudo apt install python3-pyqt6"
    echo "  Fedora:        sudo dnf install python3-pyqt6"
    exit 1
fi

# Create app directory and download script
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR"
curl -fsSL "$SCRIPT_URL" -o "$APP_DIR/main.py"

# Create launcher script
cat > "$BIN_DIR/imggone" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DIR/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/imggone"

# Create .desktop file for KDE/GNOME app menu
cat > "$DESKTOP_DIR/imggone.desktop" <<EOF
[Desktop Entry]
Name=ImgGone
Comment=Find and delete corrupted image files
Exec=$BIN_DIR/imggone
Icon=image-x-generic
Type=Application
Categories=Utility;Graphics;
Keywords=image;corrupt;delete;clean;
EOF

echo ""
echo "ImgGone installed!"
echo "  Launch from terminal: imggone"
echo "  Or find it in your app menu as 'ImgGone'"
echo ""
echo "To uninstall, run: curl -fsSL $UNINSTALL_URL | bash"