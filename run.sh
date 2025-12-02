#!/bin/bash
# Simple script to run the web application using uv

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "Or visit: https://github.com/astral-sh/uv"
    exit 1
fi

# Sync dependencies (creates venv if needed and installs dependencies)
echo "📦 Syncing dependencies with uv..."
uv sync

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY environment variable is not set"
    echo "You can set it with: export OPENAI_API_KEY='your-key-here'"
    echo ""
fi

# Run the application using uv
echo "🚀 Starting Gradio web application..."
echo "Open http://localhost:7860 in your browser"
echo "Press Ctrl+C to stop"
echo ""

uv run python app.py

