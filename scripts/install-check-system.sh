#!/bin/bash

################################################################################
#
#  📦 INSTALL CHECK-SYSTEM SHORTCUTS & ALIASES
#
#  Sets up convenient access to check-system.sh diagnostic script
#
#  Usage: ./install-check-system.sh
#
################################################################################

set -e

echo "📦 Installing check-system shortcuts..."
echo ""

# Detect if running from repo or standalone
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHECK_SCRIPT="$SCRIPT_DIR/check-system.sh"

if [ ! -f "$CHECK_SCRIPT" ]; then
    echo "❌ Error: check-system.sh not found at $CHECK_SCRIPT"
    exit 1
fi

echo "✅ Found check-system.sh at: $CHECK_SCRIPT"
echo ""

# ====== BASHRC ALIASES ======

echo "📝 Adding bash aliases..."

BASHRC="${HOME}/.bashrc"

# Remove old aliases if they exist
sed -i '/^alias check-/d' "$BASHRC" 2>/dev/null || true

# Add new aliases
cat >> "$BASHRC" << EOF

# ⛵ Midnight Rider navigation system aliases
alias check-system='$CHECK_SCRIPT'
alias check-quick='$CHECK_SCRIPT --quick'
alias check-full='$CHECK_SCRIPT --full'
alias check-watch='$CHECK_SCRIPT --watch'

EOF

echo "✅ Aliases added to $BASHRC"
echo ""

# ====== DESKTOP SHORTCUT (OPTIONAL) ======

if [ -d "$HOME/Desktop" ]; then
    echo "🖥️  Creating desktop shortcut..."
    
    DESKTOP_FILE="$HOME/Desktop/check-system.desktop"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Check System (Full)
Comment=Midnight Rider system health diagnostic
Icon=dialog-information
Exec=x-terminal-emulator -e $CHECK_SCRIPT --full
Terminal=false
Categories=Utility;System;

[Desktop Action Quick]
Name=Quick Check
Exec=x-terminal-emulator -e $CHECK_SCRIPT --quick

[Desktop Action Watch]
Name=Watch (Monitor)
Exec=x-terminal-emulator -e $CHECK_SCRIPT --watch
EOF
    
    chmod +x "$DESKTOP_FILE"
    echo "✅ Desktop shortcut created at: $DESKTOP_FILE"
    echo ""
else
    echo "ℹ️  Desktop folder not found (skipped desktop shortcut)"
    echo ""
fi

# ====== SUMMARY ======

echo "✅ INSTALLATION COMPLETE!"
echo ""
echo "📖 You can now use:"
echo ""
echo "  check-quick    — Quick check (services only)"
echo "  check-full     — Full diagnostic (recommended)"
echo "  check-watch    — Continuous monitoring"
echo "  check-system   — Same as check-full"
echo ""
echo "💡 Reload your shell to use aliases:"
echo "  source ~/.bashrc"
echo ""
echo "🎯 Before race deployment:"
echo "  check-full"
echo ""
