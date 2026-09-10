import network
import socket
import time
import json
from machine import RTC
import ntptime
from wifimanager import WiFiManager

def main():
    """Main application entry point"""
    wm = WiFiManager()
    
    # Check if WiFi credentials are stored
    if wm.has_credentials():
        print("Connecting to saved WiFi...")
        if wm.connect():
            print("Connected successfully!")
            # Sync time with NTP server
            wm.sync_time()
            # Your application code here
            run_app()
        else:
            print("Failed to connect, starting AP mode...")
            wm.start_ap_mode()
    else:
        print("No credentials found, starting AP mode...")
        wm.start_ap_mode()

def run_app():
    """Your main application runs here"""
    rtc = RTC()
    while True:
        # Get current time
        time_tuple = rtc.datetime()
        print(f"Current time: {time_tuple}")
        time.sleep(10)

if __name__ == "__main__":
    main()
