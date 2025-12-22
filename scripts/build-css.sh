#!/usr/bin/env bash
# Build Tailwind CSS + DaisyUI (proper npm integration)
set -euo pipefail
cd "$(dirname "$0")/.."

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Build CSS
echo "Building Tailwind + DaisyUI..."
npm run build:css

echo "Done! Output: app/static/tailwind.css"
ls -lh app/static/tailwind.css
