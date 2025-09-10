#!/usr/bin/env python3
"""
Script to create Chrome profiles for browser automation.
This script will create the profile directories and optionally launch Chrome
for manual Google sign-in.
"""

import os
import subprocess
import sys
from pathlib import Path
import time

def create_profile_directories(base_dir: str, num_profiles: int = 3):
    """Create the profile directories."""
    base_path = Path(base_dir).expanduser()
    
    print(f"Creating profile directories in: {base_path}")
    
    for i in range(num_profiles):
        profile_path = base_path / f"profile_{i}"
        profile_path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {profile_path}")

def launch_chrome_for_profile(profile_path: str, profile_name: str):
    """Launch Chrome with a specific profile directory."""
    try:
        cmd = [
            "google-chrome",
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
        
        print(f"Launching Chrome for {profile_name}...")
        print(f"Command: {' '.join(cmd)}")
        
        # Launch Chrome in background
        process = subprocess.Popen(cmd)
        print(f"Chrome launched for {profile_name} (PID: {process.pid})")
        return process
        
    except FileNotFoundError:
        print("Error: google-chrome not found. Make sure Chrome is installed.")
        return None
    except Exception as e:
        print(f"Error launching Chrome for {profile_name}: {e}")
        return None

def main():
    # Configuration
    base_dir = "~/.config/browseruse/profiles"
    num_profiles = 3
    
    print("=== Chrome Profile Creation Script ===")
    print(f"Base directory: {base_dir}")
    print(f"Number of profiles: {num_profiles}")
    print()
    
    # Create directories
    create_profile_directories(base_dir, num_profiles)
    print()
    
    # Ask user if they want to launch Chrome for manual sign-in
    response = input("Do you want to launch Chrome for each profile to sign into Google? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        base_path = Path(base_dir).expanduser()
        processes = []
        
        print("\nLaunching Chrome instances...")
        print("Please sign into Google on each Chrome window that opens.")
        print("You can close each Chrome window after signing in.")
        print()
        
        for i in range(num_profiles):
            profile_path = base_path / f"profile_{i}"
            profile_name = f"profile_{i}"
            
            process = launch_chrome_for_profile(str(profile_path), profile_name)
            if process:
                processes.append(process)
            
            # Wait a bit between launches
            time.sleep(2)
        
        print(f"\nLaunched {len(processes)} Chrome instances.")
        print("Please sign into Google on each profile, then close the Chrome windows.")
        print("The profiles will be saved automatically.")
        
        # Wait for user to finish
        input("\nPress Enter when you've finished signing into all profiles...")
        
        # Close all Chrome processes
        print("Closing Chrome instances...")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        print("Done!")
    
    else:
        print("Skipping Chrome launch. You can manually launch Chrome with:")
        print(f"google-chrome --user-data-dir=~/.config/browseruse/profiles/profile_X")
        print("where X is 0, 1, or 2")

if __name__ == "__main__":
    main() 