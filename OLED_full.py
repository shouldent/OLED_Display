# --- BLINKA BUG HOTFIX FOR PYTHON 3.12+ ---
import sys
from tkinter import font
import microcontroller
sys.modules['microcontroller.pin'] = microcontroller.pin
microcontroller.pin.i2cPorts = ()
# ------------------------------------------
import os
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

# Adding libraries for Google Calendar API
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Global variables for the calendar background thread
next_meeting_title = "Loading..."
next_meeting_time = ""
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

scroll_x = 0
last_scroll_update = time.time()

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

def update_calendar_loop():
    global next_meeting_title, next_meeting_time
    while True:
        try:
            creds = None
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    next_meeting_title = "Auth Required"
                    next_meeting_time = "Check PC"
                    time.sleep(60)
                    continue
            
            service = build('calendar', 'v3', credentials=creds)
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(calendarId='primary', timeMin=now,
                                                  maxResults=1, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])
            
            if not events:
                next_meeting_title = "No meetings today"
                next_meeting_time = "Day off! 😎"
            else:
                event = events[0]
                summary = event.get('summary', 'Untitled Meeting')
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                next_meeting_title = summary
                
                # --- AQUÍ ESTÁ EL AJUSTE INGLÉS ---
                if 'T' in start:
                    # Dividimos fecha y hora (ej: "2026-06-07T18:00:00")
                    date_part, time_part = start.split('T')
                    time_str = time_part[:5]  # Extrae "18:00"
                    
                    # Obtenemos la fecha de hoy en formato local (YYYY-MM-DD)
                    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
                    
                    if date_part == today_str:
                        next_meeting_time = f"Today {time_str}"
                    else:
                        # Si es otro día, parseamos para mostrar las primeras letras del día (ej: "Sun")
                        event_date = datetime.datetime.strptime(date_part, '%Y-%m-%d')
                        day_name = event_date.strftime('%a') # "Sun", "Mon", etc.
                        next_meeting_time = f"{day_name} {time_str}"
                else:
                    next_meeting_time = "All day event"
                    
                next_meeting_title = summary
                
        except Exception as e:
            next_meeting_title = "Calendar Error"
            next_meeting_time = ""
            
        # Wait 10 minutes (600 seconds) before checking Google Calendar again
        time.sleep(600)

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

# Start the Google Calendar background worker thread
threading.Thread(target=update_calendar_loop, daemon=True).start()

# Check if the credentials file exists before starting the calendar feature
dir_path = os.path.dirname(os.path.realpath(__file__))
credentials_path = os.path.join(dir_path, 'credentials.json')

calendar_enabled = False

if os.path.exists(credentials_path):
    calendar_enabled = True
    threading.Thread(target=update_calendar_loop, daemon=True).start()
else:
    print("[WARNING] credentials.json not found. Calendar screen will be skipped.")


while True:
    # Constantly calculate network speed on each cycle
    calculate_network_speed()

    # Clear canvas
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    
    # Update weather data every 5 minutes
    if time.time() - last_network_update > 300:
        update_weather()
        last_network_update = time.time()

    # 1. Determine how long the screen should stay active
    if current_screen == 5 and calendar_enabled:
        screen_timeout = 10  # 10 seconds for the calendar to let the text scroll
    else:
        screen_timeout = 4   # 4 seconds for system performance metrics

    # 2. Check if it's time to switch screens
    if time.time() - last_screen_change > screen_timeout:
        current_screen = (current_screen + 1) % 6
        scroll_x = 0  # Reset scroll position to the right edge for the next loop
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

    # --- SCREEN 5: NEXT MEETING ---
    elif current_screen == 5:
        # 1. Draw static header
        draw.text((0, 0), "NEXT MEETING:", font=font_small, fill=255)
        
        # 2. Setup text
        full_text = f"{next_meeting_title} - {next_meeting_time}"
        text_width = font_small.getlength(full_text)
        display_width = 128
        
        draw.text((scroll_x, 16), full_text, font=font_small, fill=255)
        
       # 3. Dynamic scrolling logic
        if text_width > display_width:
            scroll_x -= 4

            if scroll_x < -text_width:
                scroll_x = display_width
        else:
            scroll_x = 0

    oled.image(image)
    oled.show()
    time.sleep(0.2)