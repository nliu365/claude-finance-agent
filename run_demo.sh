#!/bin/bash
# Demo script - Run a quick analysis on one company

source .venv/bin/activate

echo "🚀 Running Finance Agent Demo"
echo "================================"
echo ""
echo "📊 Analyzing sample 10-K filing..."
echo ""

# Run from project root directory
python scripts/finance_analyzer.py data/10k_2020_10_critical_sections/1137091_2020.json

echo ""
echo "✅ Demo complete!"
echo "📁 Check data/results/ for detailed JSON output"
