#!/bin/bash
# Install Midnight Rider Dashboard shortcut on macOS

WORKSPACE="/Users/aneto/.openclaw/workspace"
DESKTOP="$HOME/Desktop"

echo "📌 Installing Midnight Rider Dashboard Shortcut (macOS)"
echo ""

# Create .app bundle for macOS
APP_DIR="$DESKTOP/Midnight Rider Dashboard.app/Contents"
mkdir -p "$APP_DIR/MacOS"
mkdir -p "$APP_DIR/Resources"

# Create macOS launcher script
cat > "$APP_DIR/MacOS/launcher" << 'EOF'
#!/bin/bash
cd /home/aneto/.openclaw/workspace
python3 -m http.server 8888 > /dev/null 2>&1 &
sleep 1
open "http://localhost:8888"
EOF
chmod +x "$APP_DIR/MacOS/launcher"

# Create Info.plist
cat > "$APP_DIR/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.midnightrider.dashboard</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Midnight Rider Dashboard</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
</dict>
</plist>
EOF

# Copy icon (convert SVG to ICNS if available, else use SVG)
if command -v sips &> /dev/null; then
    echo "🎨 Converting icon to macOS format..."
    sips -s format icns "$WORKSPACE/midnight-rider-icon.svg" --out "$APP_DIR/Resources/icon.icns"
else
    echo "🎨 Copying icon (SVG)..."
    cp "$WORKSPACE/midnight-rider-icon.svg" "$APP_DIR/Resources/"
fi

echo ""
echo "✅ macOS Installation Complete!"
echo ""
echo "📍 App location: $DESKTOP/Midnight Rider Dashboard.app"
echo ""
echo "🚀 You can now:"
echo "   • Double-click the app on Desktop to open Dashboard"
echo "   • Or add to Dock (drag app to Dock)"
echo "   • Or use Spotlight search (Cmd+Space, type 'Midnight Rider')"
echo ""
echo "💡 Tips:"
echo "   • The app opens http://localhost:3001/dashboard-portal.html"
echo "   • Make sure Grafana is running before clicking"
echo "   • Works on macOS 10.12+"
echo ""
