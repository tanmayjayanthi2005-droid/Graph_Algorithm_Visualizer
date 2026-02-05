#!/bin/bash
# Quick-start script for Graph Algorithm Visualizer

echo "======================================================"
echo "  Graph Algorithm Visualizer — Quick Start"
echo "======================================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --break-system-packages -q
echo "✓ Dependencies installed"
echo ""

# Run the server
echo "🚀 Starting Flask server..."
echo "   Open your browser and navigate to:"
echo ""
echo "   👉  http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop the server."
echo ""
python3 main.py
