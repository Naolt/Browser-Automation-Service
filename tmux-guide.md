# Persistent Browser Automation with tmux

This guide explains how to use [`tmux`](https://github.com/tmux/tmux/wiki) to run your browser automation system persistently on a remote virtual machine (VM). With `tmux`, your Chrome instances and API service will continue running even if your SSH connection drops.

---

## 🧠 Why Use tmux?

When working with long-running browser automation processes, the default SSH connection can be unreliable. If the SSH session closes or disconnects, any process you were running also stops.

`tmux` solves this by allowing you to:

- Run **Chrome instances** and **API service** in persistent terminal sessions
- **Detach** from sessions without stopping anything
- **Reconnect** later from the same or different machine
- **Monitor** Chrome processes and API service status remotely

---

## 🏗️ System Architecture

Our browser automation system consists of two main components:

1. **Chrome Profile Launcher** - Manages Chrome instances with automatic restart
2. **API Service** - FastAPI service that connects to Chrome instances via CDP

Both components need to run persistently for the system to work properly.

---

## 🧰 Prerequisites

Make sure `tmux` is installed on your VM. If not, install it:

```bash
sudo apt update
sudo apt install tmux -y
```

Also ensure you have:

- Python 3.8+ installed
- Google Chrome browser installed
- Chrome profiles created and authenticated (`python create_profiles.py`)

---

## 🚀 Setting Up Persistent Sessions

### 1. Start Chrome Profile Launcher Session

```bash
# Create a new tmux session for Chrome instances
tmux new -s chrome_launcher

# In the tmux session, launch Chrome instances
python launch_chrome_profiles.py
```

This will:

- Launch 3 Chrome instances on ports 9222, 9223, 9224
- Start automatic monitoring for crashes
- Restart crashed instances automatically
- Show status with 's' command

### 2. Detach from Chrome Launcher Session

Press the following key combo to detach:

```
Ctrl + B, then D
```

Your Chrome instances will continue running in the background.

### 3. Start API Service Session

```bash
# Create a new tmux session for the API service
tmux new -s api_service

# In the tmux session, start the API service
python main.py
```

### 4. Detach from API Service Session

Press the following key combo to detach:

```
Ctrl + B, then D
```

Both your Chrome instances and API service are now running persistently.

---

## 🔍 Monitoring Your Sessions

### Check Chrome Launcher Status

```bash
# Reattach to Chrome launcher session
tmux attach -t chrome_launcher

# Press 's' to see Chrome process status
# You should see something like:
# 📊 Current Chrome Process Status:
#   ✅ profile_0: port 9222 (PID: 12340) - Running
#   ✅ profile_1: port 9223 (PID: 12367) - Running
#   ✅ profile_2: port 9224 (PID: 12350) - Running

# Detach again with Ctrl + B, then D
```

### Check API Service Status

```bash
# Reattach to API service session
tmux attach -t api_service

# You should see logs like:
# TaskService started with 3 worker(s).
# Worker 0 started.
# Worker 1 started.
# Worker 2 started.

# Detach again with Ctrl + B, then D
```

---

## 🧼 Managing tmux Sessions

### List All Sessions

```bash
tmux ls
```

You should see both sessions:

```
chrome_launcher: 1 windows
api_service: 1 windows
```

### Reattach to Sessions

```bash
# Reattach to Chrome launcher
tmux attach -t chrome_launcher

# Reattach to API service
tmux attach -t api_service
```

### Kill Sessions (if needed)

```bash
# Kill Chrome launcher session
tmux kill-session -t chrome_launcher

# Kill API service session
tmux kill-session -t api_service
```

---

## 🔄 Recovery Scenarios

### Chrome Instance Crashes

If Chrome instances crash, the launcher will automatically restart them:

```
⚠️  Chrome process for profile_1 (PID: 12345) has crashed. Restarting...
✅ Successfully restarted profile_1 (new PID: 12367)
```

### API Service Issues

If the API service encounters issues:

1. **Reattach to API service session**: `tmux attach -t api_service`
2. **Check logs** for error messages
3. **Restart if needed**: Stop with Ctrl+C, then run `python main.py` again
4. **Detach**: Ctrl + B, then D

### Complete System Restart

If you need to restart everything:

```bash
# Kill all sessions
tmux kill-session -t chrome_launcher
tmux kill-session -t api_service

# Start Chrome launcher
tmux new -s chrome_launcher -d "python launch_chrome_profiles.py"

# Start API service
tmux new -s api_service -d "python main.py"
```

---

## 📊 Monitoring Commands

### Check System Health

```bash
# Check if Chrome instances are running
curl http://localhost:9222/json/version

# Check API service health
curl http://localhost:8000/docs

# Check Chrome process status
tmux send-keys -t chrome_launcher 's' Enter
```

### View Logs

```bash
# View Chrome launcher logs
tmux capture-pane -t chrome_launcher -S - -E -

# View API service logs
tmux capture-pane -t api_service -S - -E -
```

---

## ✅ Best Practices

- **Use descriptive session names** (`chrome_launcher`, `api_service`)
- **Always detach** (`Ctrl + B`, `D`) before closing SSH
- **Monitor regularly** - Check session status with `tmux ls`
- **Keep sessions separate** - Chrome launcher and API service in different sessions
- **Document your setup** - Note session names and startup commands

---

## 🚨 Troubleshooting

### Sessions Not Starting

```bash
# Check if tmux is running
ps aux | grep tmux

# Check if ports are available
netstat -tlnp | grep :922
netstat -tlnp | grep :8000
```

### Chrome Instances Not Responding

```bash
# Reattach to Chrome launcher
tmux attach -t chrome_launcher

# Check status with 's' command
# Look for any error messages
# Restart if needed with Ctrl+C, then python launch_chrome_profiles.py
```

### API Service Not Responding

```bash
# Reattach to API service
tmux attach -t api_service

# Check for error messages
# Restart if needed with Ctrl+C, then python main.py
```

---

## 🧩 Advanced Configuration

### Auto-Start Script

Create a startup script `start_browser_automation.sh`:

```bash
#!/bin/bash
# Start Chrome launcher
tmux new-session -d -s chrome_launcher "cd /path/to/browser-use-api && python launch_chrome_profiles.py"

# Wait for Chrome instances to start
sleep 10

# Start API service
tmux new-session -d -s api_service "cd /path/to/browser-use-api && python main.py"

echo "Browser automation system started!"
echo "Chrome launcher: tmux attach -t chrome_launcher"
echo "API service: tmux attach -t api_service"
```

### Systemd Service (Optional)

For production deployments, consider using systemd services instead of tmux for better process management and automatic restart capabilities.

---

## 📝 Quick Reference

| Command                                | Description                   |
| -------------------------------------- | ----------------------------- |
| `tmux new -s chrome_launcher`          | Start Chrome launcher session |
| `tmux new -s api_service`              | Start API service session     |
| `tmux ls`                              | List all sessions             |
| `tmux attach -t chrome_launcher`       | Reattach to Chrome launcher   |
| `tmux attach -t api_service`           | Reattach to API service       |
| `tmux kill-session -t chrome_launcher` | Kill Chrome launcher session  |
| `Ctrl + B, then D`                     | Detach from current session   |
| `Ctrl + B, then %`                     | Split window vertically       |
| `Ctrl + B, then "`                     | Split window horizontally     |
