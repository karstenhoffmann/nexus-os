#!/usr/bin/env bash
# Build Tailwind CSS from templates (offline-first, no Node.js required)
set -euo pipefail
cd "$(dirname "$0")/.."

# Download Tailwind CLI if not present
if [ ! -f "./tailwindcss" ]; then
    echo "Downloading Tailwind CLI (standalone, no Node.js)..."
    curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
    chmod +x tailwindcss-macos-arm64
    mv tailwindcss-macos-arm64 tailwindcss
fi

# Build CSS
echo "Building Tailwind CSS..."
./tailwindcss -i app/static/tailwind-input.css -o app/static/tailwind.css --minify

echo "Done! Output: app/static/tailwind.css"
ls -lh app/static/tailwind.css
