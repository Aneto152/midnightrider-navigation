#!/bin/bash
# Install Midnight Rider Dashboard shortcut on desktop

WORKSPACE="/home/aneto/.openclaw/workspace"
DESKTOP="$HOME/Desktop"

echo "📌 Installing Midnight Rider Dashboard Shortcut"
echo ""

# Check if Desktop exists
if [ ! -d "$DESKTOP" ]; then
    echo "📁 Creating Desktop folder..."
    mkdir -p "$DESKTOP"
fi

# Copy .desktop file to Desktop
echo "📋 Installing desktop shortcut..."
cp "$WORKSPACE/Midnight-Rider-Dashboard.desktop" "$DESKTOP/"

# Make it executable
chmod +x "$DESKTOP/Midnight-Rider-Dashboard.desktop"

# Copy icon
echo "🎨 Copying icon..."
cp "$WORKSPACE/midnight-rider-icon.svg" "$DESKTOP/"

# Trust the .desktop file (for GNOME)
echo "🔐 Trusting shortcut..."
gio set "$DESKTOP/Midnight-Rider-Dashboard.desktop" metadata::trusted true 2>/dev/null || true

echo ""
echo "✅ Installation Complete!"
echo ""
echo "📍 Shortcut location: $DESKTOP/Midnight-Rider-Dashboard.desktop"
echo "🎨 Icon location: $DESKTOP/midnight-rider-icon.svg"
echo ""
echo "🚀 You can now:"
echo "   • Double-click the shortcut on Desktop to open Dashboard"
echo "   • Or right-click Desktop → Create Link to Application"
echo ""
echo "💡 Tips:"
echo "   • The shortcut opens http://localhost:3001/dashboard-portal.html"
echo "   • Make sure Grafana is running before clicking"
echo "   • Grafana must be accessible at localhost:3001"
echo ""
