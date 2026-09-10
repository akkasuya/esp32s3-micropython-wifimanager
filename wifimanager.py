import network
import socket
import json
import os
import time
import ntptime
from machine import RTC

class WiFiManager:
    """WiFi Manager for ESP32 S3 - Similar to Arduino WiFiManager"""
    
    def __init__(self, config_file="wifi_config.json"):
        self.config_file = config_file
        self.wlan = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.config = self.load_config()
        
    def load_config(self):
        """Load WiFi configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return {"ssid": "", "password": "", "ntp_server": "pool.ntp.org"}
    
    def save_config(self, ssid, password, ntp_server="pool.ntp.org"):
        """Save WiFi configuration to file"""
        self.config = {
            "ssid": ssid,
            "password": password,
            "ntp_server": ntp_server
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f)
            return True
        except:
            return False
    
    def has_credentials(self):
        """Check if credentials are saved"""
        return self.config.get("ssid") and self.config.get("password")
    
    def connect(self, timeout=10):
        """Connect to WiFi with saved credentials"""
        if not self.has_credentials():
            return False
        
        self.wlan.active(True)
        ssid = self.config["ssid"]
        password = self.config["password"]
        
        print(f"Connecting to {ssid}...")
        self.wlan.connect(ssid, password)
        
        start_time = time.time()
        while not self.wlan.isconnected():
            if time.time() - start_time > timeout:
                print("Connection timeout")
                return False
            time.sleep(1)
        
        ifconfig = self.wlan.ifconfig()
        print(f"Connected! IP: {ifconfig[0]}")
        return True
    
    def start_ap_mode(self, ssid="ESP32-Setup", password="12345678"):
        """Start WiFi Access Point for configuration"""
        self.ap.active(True)
        self.ap.config(essid=ssid, password=password)
        
        print(f"AP Mode started!")
        print(f"SSID: {ssid}")
        print(f"Password: {password}")
        print(f"IP: {self.ap.ifconfig()[0]}")
        
        # Start web server for configuration
        self.start_web_server()
    
    def start_web_server(self, port=80):
        """Start HTTP server for WiFi configuration"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(5)
        
        print(f"Web server started on port {port}")
        print("Visit: http://192.168.4.1")
        
        try:
            while True:
                client, addr = server_socket.accept()
                print(f"Client connected from {addr}")
                
                request = client.recv(1024).decode()
                if request:
                    response = self.handle_request(request)
                    client.send(response)
                
                client.close()
        except KeyboardInterrupt:
            print("Web server stopped")
            server_socket.close()
    
    def handle_request(self, request):
        """Handle HTTP requests"""
        print(f"Request:\n{request}")
        
        # Handle GET request - show configuration page
        if request.startswith("GET / "):
            return self.get_config_page()
        
        # Handle POST request - save WiFi credentials
        elif request.startswith("POST /save "):
            # Parse form data
            body_start = request.find("\r\n\r\n")
            if body_start != -1:
                body = request[body_start + 4:]
                params = self.parse_form_data(body)
                
                ssid = params.get("ssid", "")
                password = params.get("password", "")
                ntp_server = params.get("ntp_server", "pool.ntp.org")
                
                if ssid and password:
                    if self.save_config(ssid, password, ntp_server):
                        response = self.get_success_page()
                        print(f"Credentials saved - SSID: {ssid}")
                        return response
            
            return self.get_error_page("Failed to save configuration")
        
        # Handle GET request for status
        elif request.startswith("GET /status "):
            return self.get_status_json()
        
        return self.get_404_page()
    
    def parse_form_data(self, body):
        """Parse form data from POST request"""
        params = {}
        pairs = body.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                # Simple URL decode
                value = value.replace('+', ' ')
                params[key] = value
        return params
    
    def get_config_page(self):
        """Return HTML configuration page"""
        html = """HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: {length}

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 WiFi Manager</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 500px; margin: 50px auto; }}
        .container {{ background: #f0f0f0; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; text-align: center; }}
        form {{ display: flex; flex-direction: column; }}
        label {{ margin-top: 15px; font-weight: bold; color: #555; }}
        input, select {{ padding: 10px; margin-top: 5px; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ margin-top: 20px; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
        button:hover {{ background: #0056b3; }}
        .info {{ background: #e7f3ff; padding: 15px; margin-bottom: 20px; border-radius: 5px; color: #004085; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 ESP32 WiFi Setup</h1>
        <div class="info">
            <strong>Setup Instructions:</strong><br>
            Enter your WiFi network details and NTP server to sync time.
        </div>
        <form method="POST" action="/save">
            <label for="ssid">WiFi Network (SSID):</label>
            <input type="text" id="ssid" name="ssid" placeholder="Your WiFi name" required>
            
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" placeholder="Your WiFi password" required>
            
            <label for="ntp_server">NTP Server (for time sync):</label>
            <input type="text" id="ntp_server" name="ntp_server" value="pool.ntp.org" placeholder="pool.ntp.org">
            
            <button type="submit">💾 Save Configuration</button>
        </form>
    </div>
</body>
</html>"""
        
        body = html.split('\n\n', 1)[1]
        content_length = len(body)
        return html.format(length=content_length)
    
    def get_success_page(self):
        """Return success page"""
        html = """HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Setup Complete</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }}
        .success {{ color: green; font-size: 24px; }}
    </style>
</head>
<body>
    <div class="success">
        <h1>✓ Configuration Saved!</h1>
        <p>ESP32 will now restart and connect to the WiFi network.</p>
        <p>Please wait a few seconds...</p>
    </div>
    <script>
        setTimeout(function() {
            window.location.href = '/';
        }, 3000);
    </script>
</body>
</html>"""
        return html
    
    def get_error_page(self, message):
        """Return error page"""
        html = f"""HTTP/1.1 400 Bad Request
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }}
        .error {{ color: red; font-size: 20px; }}
    </style>
</head>
<body>
    <div class="error">
        <h1>✗ Error</h1>
        <p>{message}</p>
        <a href="/">Back to Setup</a>
    </div>
</body>
</html>"""
        return html
    
    def get_404_page(self):
        """Return 404 page"""
        html = """HTTP/1.1 404 Not Found
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>404 Not Found</title>
</head>
<body>
    <h1>404 - Page Not Found</h1>
</body>
</html>"""
        return html
    
    def get_status_json(self):
        """Return JSON status"""
        status = {
            "ssid": self.config.get("ssid", ""),
            "connected": self.wlan.isconnected(),
            "ap_enabled": self.ap.active()
        }
        if self.wlan.isconnected():
            ifconfig = self.wlan.ifconfig()
            status["ip"] = ifconfig[0]
        
        response = f"""HTTP/1.1 200 OK
Content-Type: application/json

{json.dumps(status)}"""
        return response
    
    def sync_time(self, ntp_server=None):
        """Sync time with NTP server"""
        if ntp_server is None:
            ntp_server = self.config.get("ntp_server", "pool.ntp.org")
        
        try:
            print(f"Syncing time with {ntp_server}...")
            ntptime.server = ntp_server
            ntptime.settime()
            
            rtc = RTC()
            time_tuple = rtc.datetime()
            print(f"Time synced: {time_tuple}")
            return True
        except Exception as e:
            print(f"Failed to sync time: {e}")
            return False
    
    def reset_config(self):
        """Reset configuration"""
        try:
            os.remove(self.config_file)
            self.config = {"ssid": "", "password": "", "ntp_server": "pool.ntp.org"}
            return True
        except:
            return False
