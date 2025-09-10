#!/bin/bash

# Browser API Startup Script
# This script sets up the environment and starts Chrome profiles and API service

echo "🚀 Starting Browser API System..."

# Set Chrome to headless mode for VM environment
export CHROME_HEADLESS=true

# Optional: Set up virtual display if needed (uncomment if you want GUI)
# sudo apt update && sudo apt install xvfb -y
# Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
# export DISPLAY=:99

# Start Chrome Profile Launcher in tmux
echo "📱 Starting Chrome Profile Launcher..."
tmux new-session -d -s chrome_launcher "cd $(pwd) && python launch_chrome_profiles.py"

# Wait for Chrome instances to start
echo "⏳ Waiting for Chrome instances to start..."
sleep 10

# Start API Service in tmux
echo "🌐 Starting API Service..."
tmux new-session -d -s api_service "cd $(pwd) && python main.py"

echo "✅ Browser automation system started!"
echo ""
echo "📋 Session Management:"
echo "  Chrome launcher: tmux attach -t chrome_launcher"
echo "  API service:     tmux attach -t api_service"
echo "  List sessions:   tmux ls"
echo "  Kill sessions:   tmux kill-session -t chrome_launcher && tmux kill-session -t api_service"
echo ""
echo "🔍 Check status:"
echo "  Chrome instances: curl http://localhost:9222/json/version"
echo "  API service:      curl http://localhost:8000/docs"
