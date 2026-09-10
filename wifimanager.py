import network
import socket
import json
import os
import time
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
            return {"ssid": "", "password": "", "timezone": 0}
    
    def save_config(self, ssid, password, timezone=0):
        """Save WiFi configuration to file"""
        self.config = {
            "ssid": ssid,
            "password": password,
            "timezone": int(timezone)
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
    
    def get_timezone(self):
        """Get timezone offset from config"""
        return self.config.get("timezone", 0)
    
    def get_ssid(self):
        """Get saved SSID"""
        return self.config.get("ssid", "")
    
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
                timezone = params.get("timezone", "0")
                
                if ssid and password:
                    if self.save_config(ssid, password, timezone):
                        response = self.get_success_page()
                        print(f"Credentials saved - SSID: {ssid}, Timezone: {timezone}")
                        return response
            
            return self.get_error_page("Failed to save configuration")
        
        # Handle POST request - update time from client
        elif request.startswith("POST /update_time "):
            body_start = request.find("\r\n\r\n")
            if body_start != -1:
                body = request[body_start + 4:]
                try:
                    data = json.loads(body)
                    timestamp = data.get("timestamp")
                    timezone = data.get("timezone", 0)
                    
                    if timestamp is not None:
                        if self.set_rtc_time(timestamp, timezone):
                            return self.get_json_response({"status": "success", "message": "Time updated"})
                        else:
                            return self.get_json_response({"status": "error", "message": "Failed to update time"}, 400)
                except:
                    return self.get_json_response({"status": "error", "message": "Invalid JSON"}, 400)
            
            return self.get_json_response({"status": "error", "message": "Missing timestamp"}, 400)
        
        # Handle GET request for current RTC time
        elif request.startswith("GET /get_time "):
            return self.get_rtc_time_json()
        
        # Handle GET request for local time (with timezone applied)
        elif request.startswith("GET /get_localtime "):
            return self.get_localtime_json()
        
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
    
    def set_rtc_time(self, timestamp, timezone=0):
        """Set RTC time from Unix timestamp with timezone offset"""
        try:
            # Convert Unix timestamp to time tuple
            # timestamp is in milliseconds, convert to seconds
            timestamp_sec = timestamp // 1000
            
            # Apply timezone offset (timezone is in hours)
            timezone_offset_sec = int(timezone) * 3600
            timestamp_sec += timezone_offset_sec
            
            # Convert Unix timestamp to (year, month, day, hour, minute, second, weekday, yearday)
            import time as time_module
            time_tuple = time_module.gmtime(timestamp_sec)
            
            # Convert to RTC format (year, month, day, weekday, hour, minute, second, microseconds)
            rtc_time = (
                time_tuple[0],           # year
                time_tuple[1],           # month
                time_tuple[2],           # day
                time_tuple[6] + 1,       # weekday (0=Monday in gmtime, but we add 1)
                time_tuple[3],           # hour
                time_tuple[4],           # minute
                time_tuple[5],           # second
                0                        # microseconds
            )
            
            rtc = RTC()
            rtc.datetime(rtc_time)
            
            # Save timezone to config so it can be used in future calculations
            tz_int = int(timezone)
            self.config["timezone"] = tz_int
            try:
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f)
            except:
                pass
            
            print(f"RTC time set to: {rtc.datetime()} (Timezone: {timezone:+d})")
            return True
        except Exception as e:
            print(f"Failed to set RTC time: {e}")
            return False
    
    def get_rtc_time_json(self):
        """Return current RTC time as JSON (UTC time)"""
        try:
            rtc = RTC()
            time_tuple = rtc.datetime()
            
            # Format: (year, month, day, weekday, hour, minute, second, microseconds)
            time_data = {
                "year": time_tuple[0],
                "month": time_tuple[1],
                "day": time_tuple[2],
                "weekday": time_tuple[3],
                "hour": time_tuple[4],
                "minute": time_tuple[5],
                "second": time_tuple[6],
                "microsecond": time_tuple[7],
                "timezone": self.config.get("timezone", 0),
                "type": "utc"
            }
            
            return self.get_json_response(time_data)
        except Exception as e:
            print(f"Failed to get RTC time: {e}")
            return self.get_json_response({"error": str(e)}, 500)
    
    def get_localtime_json(self):
        """Return current local time (UTC + timezone offset) as JSON"""
        try:
            rtc = RTC()
            time_tuple = rtc.datetime()
            
            # Calculate total seconds from RTC
            year, month, day, weekday, hour, minute, second, microsecond = time_tuple
            
            # Convert to total seconds since epoch for calculation
            import time as time_module
            # Create a simple way to add hours
            total_seconds = 0
            
            # Convert RTC time to seconds and add timezone offset
            import calendar
            dt_tuple = (year, month, day, hour, minute, second, 0, 0, 0)
            timestamp = calendar.timegm(dt_tuple)
            
            # Apply timezone offset
            timezone = self.config.get("timezone", 0)
            timezone_offset_sec = int(timezone) * 3600
            local_timestamp = timestamp + timezone_offset_sec
            
            # Convert back to time tuple
            local_time_tuple = time_module.gmtime(local_timestamp)
            
            time_data = {
                "year": local_time_tuple[0],
                "month": local_time_tuple[1],
                "day": local_time_tuple[2],
                "weekday": local_time_tuple[6],
                "hour": local_time_tuple[3],
                "minute": local_time_tuple[4],
                "second": local_time_tuple[5],
                "timezone": self.config.get("timezone", 0),
                "type": "local"
            }
            
            return self.get_json_response(time_data)
        except Exception as e:
            print(f"Failed to get local time: {e}")
            return self.get_json_response({"error": str(e)}, 500)
    
    def print_localtime(self):
        """Print current local time to console every second"""
        try:
            rtc = RTC()
            import time as time_module
            import calendar
            
            while True:
                time_tuple = rtc.datetime()
                year, month, day, weekday, hour, minute, second, microsecond = time_tuple
                
                # Convert to timestamp and apply timezone
                dt_tuple = (year, month, day, hour, minute, second, 0, 0, 0)
                timestamp = calendar.timegm(dt_tuple)
                
                timezone = self.config.get("timezone", 0)
                timezone_offset_sec = int(timezone) * 3600
                local_timestamp = timestamp + timezone_offset_sec
                
                local_time_tuple = time_module.gmtime(local_timestamp)
                
                tz_str = f"UTC{timezone:+d}" if timezone != 0 else "UTC"
                print(f"Local Time ({tz_str}): {local_time_tuple[0]:04d}-{local_time_tuple[1]:02d}-{local_time_tuple[2]:02d} {local_time_tuple[3]:02d}:{local_time_tuple[4]:02d}:{local_time_tuple[5]:02d}")
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopped printing local time")
        except Exception as e:
            print(f"Error printing local time: {e}")
    
    def get_config_page(self):
        """Return HTML configuration page with time sync and timezone"""
        # Get saved values
        saved_ssid = self.config.get("ssid", "")
        saved_timezone = self.config.get("timezone", 0)
        has_saved_ssid = bool(saved_ssid)
        
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
        body {{ font-family: Arial, sans-serif; max-width: 500px; margin: 30px auto; padding: 20px; }}
        .container {{ background: #f0f0f0; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; text-align: center; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ font-size: 18px; color: #555; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        form {{ display: flex; flex-direction: column; }}
        label {{ margin-top: 15px; font-weight: bold; color: #555; }}
        input, select {{ padding: 10px; margin-top: 5px; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ margin-top: 15px; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
        button:hover {{ background: #0056b3; }}
        .info {{ background: #e7f3ff; padding: 15px; margin-bottom: 20px; border-radius: 5px; color: #004085; }}
        .time-display {{ background: white; padding: 15px; border-radius: 5px; margin-top: 10px; text-align: center; }}
        .time-display .label {{ font-size: 12px; color: #999; margin-bottom: 5px; }}
        .time-display .time {{ font-size: 32px; font-weight: bold; color: #007bff; font-family: monospace; }}
        .time-display .date {{ font-size: 14px; color: #555; font-family: monospace; margin-top: 5px; }}
        .status {{ margin-top: 10px; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }}
        .status.success {{ background: #d4edda; color: #155724; }}
        .status.error {{ background: #f8d7da; color: #721c24; }}
        .button-group {{ display: flex; gap: 10px; }}
        .button-group button {{ flex: 1; }}
        button.secondary {{ background: #6c757d; }}
        button.secondary:hover {{ background: #5a6268; }}
        .timezone-note {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .saved-info {{ background: #fff3cd; padding: 12px; margin-bottom: 15px; border-radius: 5px; color: #856404; border-left: 4px solid #ffc107; }}
        .saved-info strong {{ color: #154360; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 ESP32 WiFi Manager</h1>
        
        {saved_section}
        
        <div class="section">
            <h2>⏰ Time Synchronization</h2>
            <div class="info">
                Your device time will be synchronized with your browser's local time.
                You can set the timezone offset to adjust for different time zones.
            </div>
            
            <div class="time-display">
                <div class="label">Client Time</div>
                <div class="time" id="clientTime">--:--:--</div>
                <div class="date" id="clientDate">----/--/--</div>
            </div>
            
            <div class="time-display">
                <div class="label">Device UTC Time</div>
                <div class="time" id="deviceTime">--:--:--</div>
                <div class="date" id="deviceDate">----/--/--</div>
            </div>
            
            <div class="time-display">
                <div class="label">Device Local Time</div>
                <div class="time" id="localTime">--:--:--</div>
                <div class="date" id="localDate">----/--/--</div>
                <div class="label" id="deviceTimezone" style="margin-top: 5px;"></div>
            </div>
            
            <label for="timezone">Timezone Offset (hours):</label>
            <input type="number" id="timezone" min="-12" max="14" step="0.5" value="{saved_timezone}" placeholder="e.g., +7 for Bangkok, -5 for New York">
            <div class="timezone-note">
                Examples: UTC+0=0, Bangkok=7, Tokyo=9, Sydney=10, London=0, New York=-5, Los Angeles=-8
            </div>
            
            <div class="button-group">
                <button type="button" onclick="updateDeviceTime()" class="secondary">🔄 Refresh Device Time</button>
                <button type="button" onclick="syncTime()">⚡ Sync Time</button>
            </div>
            <div id="timeStatus"></div>
        </div>
        
        <div class="section">
            <h2>📡 WiFi Configuration</h2>
            <div class="info">
                Enter your WiFi network details.
            </div>
            <form method="POST" action="/save">
                <label for="ssid">WiFi Network (SSID):</label>
                <input type="text" id="ssid" name="ssid" placeholder="Your WiFi name" value="{saved_ssid}" required>
                
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" placeholder="Your WiFi password" required>
                
                <label for="timezone_form">Timezone Offset (hours):</label>
                <input type="number" id="timezone_form" name="timezone" min="-12" max="14" step="0.5" value="{saved_timezone}" placeholder="e.g., +7">
                
                <button type="submit">💾 Save WiFi Configuration</button>
            </form>
        </div>
    </div>
    
    <script>
        // Format date function
        function formatDate(year, month, day) {{
            return year.toString().padStart(4, '0') + '/' + 
                   month.toString().padStart(2, '0') + '/' + 
                   day.toString().padStart(2, '0');
        }}
        
        // Update client time display every second
        function updateClientTime() {{
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            
            document.getElementById('clientTime').innerText = `${{hours}}:${{minutes}}:${{seconds}}`;
            document.getElementById('clientDate').innerText = formatDate(year, month, day);
        }}
        
        // Get device UTC time from ESP32
        function updateDeviceTime() {{
            fetch('/get_time')
                .then(response => response.json())
                .then(data => {{
                    if (data.hour !== undefined) {{
                        const hours = String(data.hour).padStart(2, '0');
                        const minutes = String(data.minute).padStart(2, '0');
                        const seconds = String(data.second).padStart(2, '0');
                        document.getElementById('deviceTime').innerText = `${{hours}}:${{minutes}}:${{seconds}}`;
                        
                        const dateStr = formatDate(data.year, data.month, data.day);
                        document.getElementById('deviceDate').innerText = dateStr;
                        
                        // Update timezone display
                        const tz = data.timezone || 0;
                        const tzStr = tz >= 0 ? `UTC+${{tz}}` : `UTC${{tz}}`;
                        document.getElementById('deviceTimezone').innerText = tzStr;
                    }}
                }})
                .catch(error => console.error('Error:', error));
        }}
        
        // Get device local time from ESP32
        function updateLocalTime() {{
            fetch('/get_localtime')
                .then(response => response.json())
                .then(data => {{
                    if (data.hour !== undefined) {{
                        const hours = String(data.hour).padStart(2, '0');
                        const minutes = String(data.minute).padStart(2, '0');
                        const seconds = String(data.second).padStart(2, '0');
                        document.getElementById('localTime').innerText = `${{hours}}:${{minutes}}:${{seconds}}`;
                        
                        const dateStr = formatDate(data.year, data.month, data.day);
                        document.getElementById('localDate').innerText = dateStr;
                    }}
                }})
                .catch(error => console.error('Error:', error));
        }}
        
        // Sync time from client to device
        function syncTime() {{
            const now = new Date();
            const timestamp = now.getTime(); // milliseconds
            const timezone = parseFloat(document.getElementById('timezone').value);
            
            const statusDiv = document.getElementById('timeStatus');
            statusDiv.innerHTML = '<div class="status">⏳ Syncing time...</div>';
            
            fetch('/update_time', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json'
                }},
                body: JSON.stringify({{ 
                    timestamp: timestamp,
                    timezone: timezone
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'success') {{
                    statusDiv.innerHTML = '<div class="status success">✓ Time synchronized successfully!</div>';
                    setTimeout(() => {{
                        updateDeviceTime();
                        updateLocalTime();
                        statusDiv.innerHTML = '';
                    }}, 1000);
                }} else {{
                    statusDiv.innerHTML = '<div class="status error">✗ Failed to sync time</div>';
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                statusDiv.innerHTML = '<div class="status error">✗ Error during sync</div>';
            }});
        }}
        
        // Initialize
        setInterval(updateClientTime, 1000);
        updateClientTime();
        updateDeviceTime();
        updateLocalTime();
        setInterval(() => {{
            updateDeviceTime();
            updateLocalTime();
        }}, 1000);
    </script>
</body>
</html>"""
        
        # Build saved section
        if has_saved_ssid:
            saved_section = f"""<div class="section">
            <div class="saved-info">
                ✓ <strong>Saved WiFi:</strong> {saved_ssid}
            </div>
        </div>"""
        else:
            saved_section = ""
        
        html_formatted = html.format(
            saved_section=saved_section,
            saved_ssid=saved_ssid,
            saved_timezone=saved_timezone
        )
        
        body = html_formatted.split('\n\n', 1)[1]
        content_length = len(body)
        return html_formatted.replace("{length}", str(content_length))
    
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
        setTimeout(function() {{
            window.location.href = '/';
        }}, 3000);
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
    
    def get_json_response(self, data, status_code=200):
        """Return JSON response"""
        json_data = json.dumps(data)
        
        status_line = "HTTP/1.1 200 OK" if status_code == 200 else f"HTTP/1.1 {status_code}"
        
        response = f"""{status_line}
Content-Type: application/json
Content-Length: {len(json_data)}

{json_data}"""
        return response
    
    def get_status_json(self):
        """Return JSON status"""
        status = {
            "ssid": self.config.get("ssid", ""),
            "connected": self.wlan.isconnected(),
            "ap_enabled": self.ap.active(),
            "timezone": self.config.get("timezone", 0)
        }
        if self.wlan.isconnected():
            ifconfig = self.wlan.ifconfig()
            status["ip"] = ifconfig[0]
        
        return self.get_json_response(status)
    
    def reset_config(self):
        """Reset configuration"""
        try:
            os.remove(self.config_file)
            self.config = {"ssid": "", "password": "", "timezone": 0}
            return True
        except:
            return False
