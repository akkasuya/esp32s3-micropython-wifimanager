# ESP32 S3 MicroPython WiFi Manager

ESP32 S3 MicroPython WiFi Manager - ตัวจัดการ WiFi ที่คล้ายกับ WiFiManager ของ Arduino พร้อมความสามารถสิงค์เวลาจากเว็บเบราว์เซอร์

## ✨ คุณสมบัติ

- 🌐 **Access Point Mode** - สร้างเครือข่ายสำหรับตั้งค่า WiFi
- 📱 **Web Configuration Interface** - หน้าเว็บสำหรับตั้งค่า SSID และ Password
- ⏰ **Time Synchronization** - รับเวลาจากเบราว์เซอร์ของผู้ใช้ผ่าน JavaScript
- 🌍 **Timezone Support** - รองรับการตั้งค่า Timezone (UTC-12 ถึง UTC+14)
- 💾 **Persistent Storage** - บันทึก WiFi credentials และ Timezone ลงในไฟล์ JSON
- 🔄 **Auto Reconnect** - เชื่อมต่อ WiFi อัตโนมัติบนครั้งถัดไป
- 📊 **Real-time Clock (RTC)** - ตั้งเวลาระบบและแสดง Local Time ทุกวินาที

## 🚀 การเริ่มต้น

### ความต้องการ
- ESP32 S3 board
- MicroPython firmware
- USB cable สำหรับ Upload

### ขั้นตอนการติดตั้ง

1. **Upload MicroPython Firmware** ไปยัง ESP32 S3

2. **Copy ไฟล์ต่อไปนี้ไปยัง ESP32:**
   - `wifimanager.py` - WiFi Manager class
   - `main.py` - Main application entry point

3. **การ Upload สามารถทำได้โดย:**
   - ใช้ Thonny IDE
   - หรือ esptool.py:
     ```bash
     esptool.py --port /dev/ttyUSB0 write_flash -z 0x1000 micropython_firmware.bin
     ```

## 📖 วิธีการใช้งาน

### โหมดพื้นฐาน

```python
from wifimanager import WiFiManager

# สร้าง instance
wm = WiFiManager()

# ตรวจสอบว่ามี credentials บันทึกไว้หรือไม่
if wm.has_credentials():
    # เชื่อมต่อ WiFi
    if wm.connect():
        print("Connected to WiFi!")
        # โค้ดของคุณ
    else:
        # ถ้าเชื่อมต่อไม่สำเร็จ เปิด AP mode
        wm.start_ap_mode()
else:
    # ไม่มี credentials บันทึกไว้ เปิด AP mode
    wm.start_ap_mode()
```

### การตั้งค่า

```python
# ตั้งค่า SSID, Password และ Timezone เอง
wm.save_config("YourSSID", "YourPassword", timezone=7)

# เชื่อมต่อ
if wm.connect():
    print("Connected!")
    
    # ดูเวลา local ของ device ทุกวินาที
    wm.print_localtime()
```

### ดึงข้อมูลเวลา

```python
from machine import RTC
import time

# ดึงเวลา RTC (UTC)
rtc = RTC()
print(f"UTC Time: {rtc.datetime()}")

# ดึงข้อมูล timezone ที่บันทึกไว้
timezone = wm.get_timezone()
print(f"Timezone: UTC{timezone:+d}")
```

## 🌐 Web Interface

### การเข้าถึง

เมื่อ ESP32 อยู่ใน AP Mode:
1. ค้นหาเครือข่าย WiFi ชื่อ `ESP32-Setup`
2. เข้าไปด้วย password: `12345678`
3. เปิดเบราว์เซอร์และไปที่ `http://192.168.4.1`

### หน้าเว็บประกอบด้วย

#### 1. **Time Synchronization**
- แสดงเวลาปัจจุบันจากเบราว์เซอร์ (Client Time)
- แสดงเวลา RTC ปัจจุบันของ ESP32 (Device UTC Time)
- แสดงเวลา Local ที่คำนวณตามโซนเวลา (Device Local Time) - อัปเดตทุก 1 วินาที
- ปุ่ม "Refresh Device Time" - โหลดเวลา RTC และ Local Time ล่าสุด
- ปุ่ม "Sync Time" - ส่งเวลาจากเบราว์เซอร์ไปยัง ESP32

#### 2. **Timezone Configuration**
- ช่องป้อนเลขโซนเวลา (-12 ถึง +14)
- ตัวอย่างโซนเวลาต่าง ๆ
- Timezone จะถูกบันทึกลงในไฟล์เพื่อใช้ในอนาคต

#### 3. **WiFi Configuration**
- ป้อน SSID ของเครือข่าย WiFi
- ป้อน Password
- ปุ่ม "Save WiFi Configuration" - บันทึกและรีสตาร์ท

## 📡 API Endpoints

### GET /
หน้าแรกแสดง HTML configuration page

### POST /save
บันทึก WiFi credentials และ timezone
```
Body: application/x-www-form-urlencoded
- ssid: เครือข่าย WiFi
- password: รหัสผ่าน
- timezone: ค่าโซนเวลา (เช่น 7, -5, 0)
```

### POST /update_time
ตั้งเวลา RTC จาก timestamp และอัปเดต timezone
```
Body: application/json
{
  "timestamp": 1694342400000,  // Unix timestamp in milliseconds
  "timezone": 7                 // Timezone offset in hours
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Time updated"
}
```

### GET /get_time
ดึงเวลา RTC ปัจจุบัน (UTC)

**Response:**
```json
{
  "year": 2023,
  "month": 9,
  "day": 10,
  "weekday": 6,
  "hour": 12,
  "minute": 30,
  "second": 45,
  "microsecond": 0,
  "timezone": 7,
  "type": "utc"
}
```

### GET /get_localtime
ดึงเวลา Local ที่คำนวณแล้ว (UTC + timezone offset)

**Response:**
```json
{
  "year": 2023,
  "month": 9,
  "day": 10,
  "weekday": 6,
  "hour": 19,
  "minute": 30,
  "second": 45,
  "timezone": 7,
  "type": "local"
}
```

### GET /status
ดึงสถานะการเชื่อมต่อ

**Response:**
```json
{
  "ssid": "YourSSID",
  "connected": true,
  "ap_enabled": false,
  "timezone": 7,
  "ip": "192.168.1.100"
}
```

## 📁 โครงสร้างไฟล์

```
esp32s3-micropython-wifimanager/
├── main.py                 # Entry point
├── wifimanager.py          # WiFiManager class
├── wifi_config.json        # WiFi credentials & timezone (auto-generated)
└── README.md              # Documentation
```

### ไฟล์ wifi_config.json
```json
{
  "ssid": "YourWiFiName",
  "password": "YourPassword",
  "timezone": 7
}
```

## 🌍 Timezone Reference

| Location | Offset | Example |
|----------|--------|---------|
| UTC | 0 | London, GMT |
| UTC+1 | 1 | Central Europe |
| UTC+7 | 7 | Bangkok, Ho Chi Minh, Jakarta |
| UTC+8 | 8 | Singapore, Hong Kong, Shanghai |
| UTC+9 | 9 | Tokyo, Seoul |
| UTC+10 | 10 | Sydney, Melbourne |
| UTC-5 | -5 | New York, Toronto |
| UTC-6 | -6 | Chicago, Mexico City |
| UTC-7 | -7 | Denver, Los Angeles |
| UTC-8 | -8 | Pacific Time |

## 🔍 Troubleshooting

### ปัญหา: ไม่สามารถเข้าถึง http://192.168.4.1

**วิธีแก้:**
1. ตรวจสอบว่าเชื่อมต่อกับเครือข่าย `ESP32-Setup` แล้ว
2. รอ 2-3 วินาทีให้ AP mode เริ่มทำงาน
3. ลองเปิด http://192.168.4.1 อีกครั้ง

### ปัญหา: เวลาไม่ตรง

**วิธีแก้:**
1. ตรวจสอบเวลาเบราว์เซอร์ว่าถูกต้องหรือไม่
2. ตรวจสอบค่า Timezone ว่าถูกต้องหรือไม่
3. กดปุ่ม "Refresh Device Time" เพื่ออัพเดทเวลา
4. ลองกดปุ่ม "Sync Time" อีกครั้ง

### ปัญหา: ESP32 ไม่เชื่อมต่อ WiFi

**วิธีแก้:**
1. ตรวจสอบ SSID และ Password ว่าถูกต้อง
2. ลบไฟล์ `wifi_config.json` และลองใหม่
3. ตรวจสอบว่า WiFi network รองรับ 2.4GHz

```python
# เพื่อรีเซ็ต configuration
wm.reset_config()
```

### ปัญหา: อ่านค่า Timezone ไม่ได้

**วิธีแก้:**
```python
# ตรวจสอบค่า timezone ที่เก็บไว้
tz = wm.get_timezone()
print(f"Saved Timezone: {tz}")

# ตรวจสอบไฟล์ config
with open("wifi_config.json", "r") as f:
    import json
    config = json.load(f)
    print(config)
```

## 💡 ตัวอย่างการใช้งาน

### Example 1: Setup พื้นฐาน

```python
from wifimanager import WiFiManager
import time

wm = WiFiManager()

if wm.has_credentials():
    if wm.connect():
        print("Connected to WiFi!")
        print(f"Timezone: UTC{wm.get_timezone():+d}")
        
        # แสดงเวลา local ทุกวินาที
        wm.print_localtime()
    else:
        wm.start_ap_mode()
else:
    wm.start_ap_mode()
```

### Example 2: ตั้งค่า WiFi, Password และ Timezone

```python
from wifimanager import WiFiManager
from machine import RTC

wm = WiFiManager()

# บันทึก configuration
wm.save_config("MyHomeWiFi", "password123", timezone=7)

if wm.connect():
    print("Connected!")
    
    # ดูเวลา
    rtc = RTC()
    print(f"UTC Time: {rtc.datetime()}")
```

### Example 3: ดึงเวลา local ทุก ๆ 5 วินาที

```python
from wifimanager import WiFiManager
from machine import RTC
import time
import calendar

wm = WiFiManager()

while True:
    rtc = RTC()
    year, month, day, weekday, hour, minute, second, microsecond = rtc.datetime()
    
    # Convert to timestamp and apply timezone
    dt_tuple = (year, month, day, hour, minute, second, 0, 0, 0)
    timestamp = calendar.timegm(dt_tuple)
    
    timezone = wm.get_timezone()
    timezone_offset_sec = int(timezone) * 3600
    local_timestamp = timestamp + timezone_offset_sec
    
    import time as time_module
    local_time = time_module.gmtime(local_timestamp)
    
    tz_str = f"UTC{timezone:+d}"
    print(f"Local Time ({tz_str}): {local_time[0]:04d}-{local_time[1]:02d}-{local_time[2]:02d} {local_time[3]:02d}:{local_time[4]:02d}:{local_time[5]:02d}")
    
    time.sleep(5)
```

## 📝 License

MIT License

## 🤝 Contributing

ยินดีรับ Pull Requests และ Issues

## ⚠️ หมายเหตุสำคัญ

- **AP Mode** จะเปิด Port 80 ดังนั้นจึงต้องใช้ HTTP (ไม่ใช่ HTTPS)
- **เวลา** จะเก็บเป็น Unix timestamp ที่มีหน่วย milliseconds จากเบราว์เซอร์
- **Credentials & Timezone** จะถูกเก็บในรูป JSON plaintext ในอุปกรณ์
- **Local Time** จะคำนวณจาก UTC time + Timezone offset
- **Timezone จะถูกบันทึกถาวร** ในไฟล์ wifi_config.json และใช้ในการคำนวณเวลา local ของทุก API call

## 🔧 เมธอดที่มีให้ใช้งาน

| เมธอด | คำอธิบาย |
|-------|---------|
| `connect()` | เชื่อมต่อ WiFi ด้วย credentials ที่บันทึกไว้ |
| `start_ap_mode()` | เปิด Access Point mode สำหรับตั้งค่า |
| `save_config()` | บันทึก SSID, Password, Timezone |
| `has_credentials()` | ตรวจสอบว่ามี credentials บันทึกไว้ |
| `get_timezone()` | ดึงค่า Timezone ที่บันทึกไว้ |
| `set_rtc_time()` | ตั้งเวลา RTC จาก Unix timestamp |
| `get_rtc_time_json()` | ดึงเวลา UTC เป็น JSON |
| `get_localtime_json()` | ดึงเวลา Local เป็น JSON |
| `print_localtime()` | พิมพ์เวลา Local ทุกวินาที (console) |
| `reset_config()` | ลบ configuration ทั้งหมด |

---

สำหรับข้อมูลเพิ่มเติม หรือปัญหาใด ๆ โปรดติดต่อหรือ สร้าง Issue
