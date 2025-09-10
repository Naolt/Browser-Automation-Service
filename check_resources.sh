#!/bin/bash
# Resource Monitoring Script

echo "�� Browser Automation Resource Monitor"
echo "======================================"
echo "Time: $(date)"
echo ""

# System Information
echo "�� System Information:"
echo "OS: $(lsb_release -d | cut -f2 2>/dev/null || echo "Linux")"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""

# Memory Usage
echo "💾 Memory Usage:"
free -h
echo ""

# CPU Load
echo "🖥️  CPU Load:"
uptime
echo ""

# Chrome Processes
echo "🌐 Chrome Processes:"
chrome_count=$(pgrep -c chrome 2>/dev/null || echo "0")
echo "Active Chrome processes: $chrome_count"

if [ $chrome_count -gt 0 ]; then
    echo "Chrome PIDs: $(pgrep chrome | tr '\n' ' ')"
    echo ""
    echo "Chrome Memory Usage:"
    ps aux | grep chrome | grep -v grep | awk '{sum+=$6} END {print "Total Chrome memory: " sum/1024 " MB"}'
fi
echo ""

# Port Usage
echo "🔌 Port Usage:"
for port in 9222 9223; do
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "✅ Port $port is in use"
    else
        echo "❌ Port $port is not in use"
    fi
done
echo ""

# API Service
echo "🚀 API Service:"
if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
    echo "✅ API service running on port 8000"
else
    echo "❌ API service not running on port 8000"
fi
echo ""

# Disk Usage
echo "💿 Profile Directory Usage:"
df -h ~/.config/browseruse/profiles 2>/dev/null || echo "Profile directory not found"
echo ""

# Resource Summary
echo "📊 Resource Summary:"
total_mem=$(free -m | grep Mem | awk '{print $2}')
available_mem=$(free -m | grep Mem | awk '{print $7}')
used_percent=$(( (total_mem - available_mem) * 100 / total_mem ))

echo "Memory Usage: ${used_percent}%"
echo "Available Memory: ${available_mem} MB"

if [ $available_mem -gt 1000 ]; then
    echo "✅ Sufficient memory available"
else
    echo "⚠️  Low memory available"
fi

if [ $chrome_count -eq 2 ]; then
    echo "✅ Expected number of Chrome instances running"
else
    echo "⚠️  Unexpected number of Chrome instances: $chrome_count (expected 2)"
fi