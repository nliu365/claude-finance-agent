#!/bin/bash
# Setup script for Finance Agent using uv
# uv is a fast Python package manager

set -e

echo "🚀 Claude Finance Agent - uv Setup"
echo "===================================="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv is not installed"
    echo ""
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo ""
    echo "✅ uv installed successfully"
    echo "   Please restart your terminal or run: source $HOME/.cargo/env"
    echo ""
    exit 0
fi

echo "✅ uv found: $(uv --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment exists"
fi

echo ""
echo "📥 Installing dependencies..."
uv pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   1. Set your API key:"
echo "      export ANTHROPIC_API_KEY='your-api-key-here'"
echo ""
echo "   2. Run the demo:"
echo "      uv run python scripts/finance_analyzer.py"
echo ""
echo "   3. Or activate the environment:"
echo "      source .venv/bin/activate"
echo "      python scripts/finance_analyzer.py"
echo ""
echo "📚 See INSTALL.md for more details"
