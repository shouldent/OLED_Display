# --- BLINKA BUG HOTFIX FOR PYTHON 3.12+ ---
import sys
import microcontroller
sys.modules['microcontroller.pin'] = microcontroller.pin
microcontroller.pin.i2cPorts = ()
# ------------------------------------------

import time
import datetime
import board
import busio
import adafruit_ssd1306
import psutil
import requests
import subprocess
import re
from PIL import Image, ImageDraw, ImageFont

# --- INTERNET SETTINGS ---
CITY = "Mexico"  # Change this to your preferred city or location
outdoor_temp = "--"
last_network_update = 0

# --- NETWORK SPEED CONTROL VARIABLES ---
last_bytes_recv = psutil.net_io_counters().bytes_recv
last_bytes_sent = psutil.net_io_counters().bytes_sent
prev_network_time = time.time()

mbps_download = 0.0
mbps_upload = 0.0

def calculate_network_speed():
    """Calculates current upload and download speeds in Mbps"""
    global last_bytes_recv, last_bytes_sent, prev_network_time, mbps_download, mbps_upload
    
    current_time = time.time()
    dt = current_time - prev_network_time
    if dt < 0.1: return # Avoid division by zero
    
    net_data = psutil.net_io_counters()
    
    # Calculate bytes difference
    bytes_download = net_data.bytes_recv - last_bytes_recv
    bytes_upload = net_data.bytes_sent - last_bytes_sent
    
    # Convert Bytes/sec to Megabits/sec (Mbps) -> (Bytes * 8) / (1024 * 1024)
    mbps_download = (bytes_download * 8) / (1024 * 1024) / dt
    mbps_upload = (bytes_upload * 8) / (1024 * 1024) / dt
    
    # Update variables for the next iteration
    last_bytes_recv = net_data.bytes_recv
    last_bytes_sent = net_data.bytes_sent
    prev_network_time = current_time

def get_network_status():
    """Detects which network interface is active and connected"""
    interfaces = psutil.net_if_stats()
    ethernet_ok = False
    wifi_ok = False
    
    for name, info in interfaces.items():
        if info.isup:
            # Filter common Linux network interface names
            if name.startswith('en') or name.startswith('eth'):
                ethernet_ok = True
            elif name.startswith('wl'):
                wifi_ok = True
                
    if ethernet_ok:
        return "Cable (Ethernet)"
    elif wifi_ok:
        # Attempt to get the WiFi network name (SSID) on Linux
        try:
            ssid = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
            return f"Wi-Fi: {ssid}" if ssid else "Wi-Fi: Connected"
        except:
            return "Wi-Fi: Connected"
    return "Disconnected"

def update_weather():
    global outdoor_temp
    try:
        weather_resp = requests.get(f"https://wttr.in/{CITY}?format=%t", timeout=3)
        if weather_resp.status_code == 200:
            outdoor_temp = weather_resp.text.strip().replace("+", "").replace("°C", "")
    except Exception:
        pass

def get_cpu_temp():
    try:
        result = subprocess.check_output(["sensors"], text=True)
        match = re.search(r'Tctl:\s*\+([0-9.]+)', result)
        if match:
            return f"{int(float(match.group(1)))} oC"
    except Exception:
        pass
    return "N/A"

# Initialize Hardware
boot_time_readable = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%H:%M (%d/%m)")
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)

font_large = ImageFont.truetype("fuente_reloj.ttf", 24)
font_small = ImageFont.load_default()

current_screen = 0
last_screen_change = time.time()

while True:
    # Constantly calculate network speed on each cycle
    calculate_network_speed()

    # Clear canvas
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    
    # Update weather data every 5 minutes
    if time.time() - last_network_update > 300:
        update_weather()
        last_network_update = time.time()

    # Rotate through 5 screens every 4 seconds
    if time.time() - last_screen_change > 4:
        current_screen = (current_screen + 1) % 5
        last_screen_change = time.time()
        
    # --- SCREEN 0: GIANT CLOCK ---
    if current_screen == 0:
        actual_time = datetime.datetime.now().strftime("%H:%M:%S")
        draw.text((0, 2), actual_time, font=font_large, fill=255)
        
    # --- SCREEN 1: PC PERFORMANCE ---
    elif current_screen == 1:
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        draw.text((0, 0), "PC SYSTEM:", font=font_small, fill=255)
        draw.text((0, 12), f"CPU: {cpu_usage}%", font=font_small, fill=255)
        draw.text((0, 22), f"RAM: {ram_usage}%", font=font_small, fill=255)
        
        # CPU progress bar
        draw.rectangle((70, 14, 120, 19), outline=255, fill=0)
        draw.rectangle((70, 14, int(70 + (cpu_usage / 2)), 19), outline=255, fill=255)
        
        # RAM progress bar
        draw.rectangle((70, 24, 120, 29), outline=255, fill=0)
        draw.rectangle((70, 24, int(70 + (ram_usage / 2)), 29), outline=255, fill=255)

    # --- SCREEN 2: PC INTERNAL SENSORS ---
    elif current_screen == 2:
        internal_temp = get_cpu_temp()
        draw.text((0, 0), "HARDWARE DETAILS:", font=font_small, fill=255)
        draw.text((0, 12), f"CPU Temp: {internal_temp}", font=font_small, fill=255)
        draw.text((0, 22), f"Up since: {boot_time_readable}", font=font_small, fill=255)

    # --- SCREEN 3: LOCAL NETWORK STATUS ---
    elif current_screen == 3:
        net_status = get_network_status()
        draw.text((0, 0), "LOCAL NETWORK:", font=font_small, fill=255)
        draw.text((0, 15), net_status, font=font_small, fill=255)

    # --- SCREEN 4: REAL-TIME NETWORK TRAFFIC ---
    elif current_screen == 4:
        draw.text((0, 0), "NET TRAFFIC:", font=font_small, fill=255)
        draw.text((0, 12), f"Down: {mbps_download:.1f} Mbps", font=font_small, fill=255)
        draw.text((0, 22), f"Up:   {mbps_upload:.1f} Mbps", font=font_small, fill=255)

    oled.image(image)
    oled.show()
    time.sleep(0.2)