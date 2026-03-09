#!/bin/bash

# ProtocolScout Flask Application Startup Script

echo "=========================================="
echo "  ProtocolScout Web Application"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file from .env.example and configure your AWS credentials"
    echo ""
    echo "Run: cp .env.example .env"
    echo "Then edit .env with your AWS credentials"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Starting Flask application..."
echo "📍 Application will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run Flask app
python app.py
