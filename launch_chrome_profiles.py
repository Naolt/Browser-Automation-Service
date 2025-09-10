#!/usr/bin/env python3
"""
Script to pre-launch Chrome instances with profiles on specific CDP ports.
This ensures the profiles are already authenticated and ready for CDP connection.
"""

import os
import subprocess
import sys
import time
import asyncio
import threading
import select
from pathlib import Path
import signal
import atexit

# Load environment variables from .env file
print("🔍 Loading environment variables...")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

try:
    from dotenv import load_dotenv
    # Force override existing environment variables
    load_dotenv(override=True)
    print("✅ .env file loaded successfully with override")
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    pass

# Configuration from environment variables with defaults
print("\n📋 Environment variable values:")
print(f"BROWSER_PROFILES_DIR: {os.getenv('BROWSER_PROFILES_DIR', 'NOT_SET')}")
print(f"CHROME_EXECUTABLE: {os.getenv('CHROME_EXECUTABLE', 'NOT_SET')}")
print(f"CHROME_START_PORT: {os.getenv('CHROME_START_PORT', 'NOT_SET')}")
print(f"CHROME_NUM_PROFILES: {os.getenv('CHROME_NUM_PROFILES', 'NOT_SET')}")
print(f"CHROME_HEADLESS: {os.getenv('CHROME_HEADLESS', 'NOT_SET')}")

# Fallback: Read .env file directly if environment variable is not set correctly
def read_env_directly():
    env_values = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_values[key] = value
    except Exception as e:
        print(f"Error reading .env file directly: {e}")
    return env_values

# Use direct reading as fallback
env_direct = read_env_directly()
if env_direct:
    print("\n📋 Direct .env file values:")
    for key in ['CHROME_HEADLESS', 'CHROME_EXECUTABLE', 'CHROME_START_PORT', 'CHROME_NUM_PROFILES']:
        if key in env_direct:
            print(f"{key}: {env_direct[key]}")

BASE_DIR = Path(os.getenv("BROWSER_PROFILES_DIR", "~/.config/browseruse/profiles")).expanduser()
CHROME_EXECUTABLE = os.getenv("CHROME_EXECUTABLE", "/usr/bin/google-chrome")
START_PORT = int(os.getenv("CHROME_START_PORT", "9222"))
NUM_PROFILES = int(os.getenv("CHROME_NUM_PROFILES", "2"))

# Use direct reading for CHROME_HEADLESS if environment variable is not correct
chrome_headless_env = os.getenv("CHROME_HEADLESS")
if chrome_headless_env is None or chrome_headless_env not in ['true', 'false']:
    chrome_headless_env = env_direct.get('CHROME_HEADLESS', 'false')
    print(f"Using direct .env value for CHROME_HEADLESS: {chrome_headless_env}")

HEADLESS = chrome_headless_env.lower() == "true"

print(f"\n🎯 Final configuration:")
print(f"BASE_DIR: {BASE_DIR}")
print(f"CHROME_EXECUTABLE: {CHROME_EXECUTABLE}")
print(f"START_PORT: {START_PORT}")
print(f"NUM_PROFILES: {NUM_PROFILES}")
print(f"HEADLESS: {HEADLESS}")

class ChromeProfileManager:
    def __init__(self):
        self.processes = []
        self.monitoring = False
        self.monitor_thread = None
        atexit.register(self.cleanup)
        
    def launch_profile(self, profile_name: str, port: int):
        """Launch a Chrome instance with a specific profile on a specific port."""
        profile_path = BASE_DIR / profile_name
        
        if not profile_path.exists():
            print(f"❌ Profile {profile_name} not found at {profile_path}")
            return None
            
        cmd = [
            CHROME_EXECUTABLE,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_path}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection"
        ]
        
        if HEADLESS:
            cmd.extend([
                "--headless",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-dev-shm-usage"
            ])
        
        print(f"🚀 Launching Chrome for {profile_name} on port {port}...")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a moment to see if it starts successfully
            time.sleep(2)
            
            if process.poll() is None:  # Process is still running
                print(f"✅ Chrome launched for {profile_name} on port {port} (PID: {process.pid})")
                return process
            else:
                stdout, stderr = process.communicate()
                print(f"❌ Failed to launch Chrome for {profile_name}:")
                print(f"STDOUT: {stdout.decode()}")
                print(f"STDERR: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"❌ Error launching Chrome for {profile_name}: {e}")
            return None
    
    def launch_all_profiles(self):
        """Launch all Chrome profiles."""
        print(f"🎯 Launching {NUM_PROFILES} Chrome profiles...")
        print(f"Base directory: {BASE_DIR}")
        print(f"Port range: {START_PORT} - {START_PORT + NUM_PROFILES - 1}")
        print()
        
        for i in range(NUM_PROFILES):
            profile_name = f"profile_{i}"
            port = START_PORT + i
            
            process = self.launch_profile(profile_name, port)
            if process:
                self.processes.append((profile_name, port, process))
            
            # Wait a bit between launches
            time.sleep(1)
        
        print(f"\n📊 Summary:")
        print(f"Successfully launched {len(self.processes)} Chrome instances:")
        for profile_name, port, process in self.processes:
            print(f"  - {profile_name}: port {port} (PID: {process.pid})")
    
    def cleanup(self):
        """Clean up all launched Chrome processes."""
        # Stop monitoring first
        self.stop_monitoring()
        
        if not self.processes:
            return
            
        print("\n🧹 Cleaning up Chrome processes...")
        for profile_name, port, process in self.processes:
            try:
                print(f"Stopping {profile_name} (PID: {process.pid})...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped {profile_name}")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {profile_name}...")
                process.kill()
            except Exception as e:
                print(f"❌ Error stopping {profile_name}: {e}")
        
        self.processes.clear()
        print("✅ Cleanup complete")
    
    def start_monitoring(self):
        """Start monitoring Chrome processes for crashes and auto-restart them."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
        self.monitor_thread.start()
        print("🔍 Started Chrome process monitoring...")
    
    def stop_monitoring(self):
        """Stop monitoring Chrome processes."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 Stopped Chrome process monitoring.")
    
    def _monitor_processes(self):
        """Monitor Chrome processes and restart them if they crash."""
        while self.monitoring:
            try:
                for i, (profile_name, port, process) in enumerate(self.processes):
                    # Check if process is still running
                    if process.poll() is not None:
                        print(f"⚠️  Chrome process for {profile_name} (PID: {process.pid}) has crashed. Restarting...")
                        
                        # Remove the crashed process
                        self.processes.pop(i)
                        
                        # Restart the process
                        new_process = self.launch_profile(profile_name, port)
                        if new_process:
                            self.processes.append((profile_name, port, new_process))
                            print(f"✅ Successfully restarted {profile_name} (new PID: {new_process.pid})")
                        else:
                            print(f"❌ Failed to restart {profile_name}")
                        
                        # Break to avoid index issues while iterating
                        break
                
                # Sleep before next check
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Error in process monitoring: {e}")
                time.sleep(10)  # Wait longer on error
    
    def get_status(self):
        """Get current status of all Chrome processes."""
        status = []
        for profile_name, port, process in self.processes:
            is_running = process.poll() is None
            status.append({
                'profile': profile_name,
                'port': port,
                'pid': process.pid,
                'running': is_running
            })
        return status
    
    def print_status(self):
        """Print current status of all Chrome processes."""
        print("\n📊 Current Chrome Process Status:")
        for status in self.get_status():
            status_icon = "✅" if status['running'] else "❌"
            print(f"  {status_icon} {status['profile']}: port {status['port']} (PID: {status['pid']}) - {'Running' if status['running'] else 'Crashed'}")

def main():
    print("=== Chrome Profile Launcher ===")
    print("This script will launch Chrome instances with pre-authenticated profiles.")
    print("Make sure you have already signed into Google on each profile!")
    print()
    
    
    # Check if profiles exist
    if not BASE_DIR.exists():
        print(f"❌ Profile directory not found: {BASE_DIR}")
        print("Please run create_profiles.py first to create the profiles.")
        return
    
    manager = ChromeProfileManager()
    
    try:
        manager.launch_all_profiles()
        
        if manager.processes:
            print(f"\n🎉 Successfully launched {len(manager.processes)} Chrome instances!")
            print("You can now start your browser automation service.")
            print("\nTo stop all Chrome instances, press Ctrl+C")
            print("To check status, press 's' and Enter")
            
            # Start monitoring for crashes
            manager.start_monitoring()
            
            # Keep the script running to maintain the Chrome instances
            try:
                while True:
                    # Check for status command
                    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                        line = input()
                        if line.strip().lower() == 's':
                            manager.print_status()
                    
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Received interrupt signal...")
        else:
            print("❌ No Chrome instances were launched successfully.")
            
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal...")
    finally:
        manager.cleanup()

if __name__ == "__main__":
    main() 