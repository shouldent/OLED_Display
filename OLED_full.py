# --- BLINKA BUG HOTFIX FOR PYTHON 3.12+ ---
import sys
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
import json
from PIL import Image, ImageDraw, ImageFont

# Adding libraries for Google Calendar API
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from fastapi import FastAPI
import uvicorn

app = FastAPI()

# Global variables for the calendar background thread
next_meeting_title = "Loading..."
next_meeting_time = ""
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

scroll_x = 0
last_scroll_update = time.time()

# --- INTERNET SETTINGS ---
CITY = "Mexico"  # Change this to your preferred city or location
weather_data = {
    "temperature": "--",
    "condition": "Unknown",
    "humidity": "--",
    "wind_speed": "--"
}

# Screen status
shared_state = {
    "manual_mode": False,
    "target_screen": None,
    "last_screen_change": time.time()
}

last_network_update = 0

# --- NETWORK SPEED CONTROL VARIABLES ---
last_bytes_recv = psutil.net_io_counters().bytes_recv
last_bytes_sent = psutil.net_io_counters().bytes_sent
prev_network_time = time.time()

mbps_download = 0.0
mbps_upload = 0.0

# Initialize Hardware
boot_time_readable = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%H:%M (%d/%m)")
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Font configuration
font_large = ImageFont.truetype("fuente_reloj.ttf", 24)
font_small = ImageFont.load_default()
font_icon = ImageFont.truetype("DejaVuSans.ttf", 16)
font_jarvis = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)

# Credentials configuration
dir_path = os.path.dirname(os.path.realpath(__file__))
credentials_path = os.path.join(dir_path, 'credentials.json')

# OLED configuration
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)

interrupt_event = threading.Event()

@app.post("/set-active/{screen_id}/{state}")
async def set_active(screen_id: str, state: str):
    new_state = (state == 'enable')
    for s in screens:
        if s["name"] == screen_id:
            s["enabled"] = new_state
            break
    status = {s['name']: s['enabled'] for s in screens}
    with open("/home/aaron/.local/share/cinnamon/desklets/jarvis_control_v2@aaron/status.json", "w") as f:
        json.dump(status, f)
    return {"message": "OK", "screen": screen_id, "enabled": new_state}

@app.post("/set-screen/{screen_name}")
async def set_screen(screen_name: str):
    shared_state["manual_mode"] = True
    shared_state["target_screen"] = screen_name
    print(f"--- API RECIBIÓ: Manual mode ON, objetivo: {screen_name} ---")
    return {"status": "ok"}

@app.post("/set-mode/auto")
async def set_mode_auto():
    shared_state["manual_mode"] = False
    shared_state["last_screen_change"] = time.time()
    return {"status": "auto_mode_active"}

def load_status():
    try:
        with open("/home/aaron/.local/share/cinnamon/desklets/jarvis_control_v2@aaron/status.json", "r") as f:
            status = json.load(f)
            for s in screens:
                if s['name'] in status:
                    s['enabled'] = status[s['name']]
            print(f"Status Loaded: {status}")
    except FileNotFoundError:
        print("No existe status.json, usando valores por defecto.")

def wait_or_interrupt(seconds):
    interrupt_event.wait(seconds)
    interrupt_event.clear()

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

def show_splash():
    splash = Image.open('splash_welcome.bmp').convert('1')
    oled.image(splash)
    oled.show()
    time.sleep(3)
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

def boot_animation(draw):
    message = "WELCOME SIR"
    for i in range(len(message) + 1):
        draw.text((0, 10), message[:i], font=font_jarvis, fill=255)
        oled.image(image)
        oled.show()
        time.sleep(0.08)
        
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
            now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
            events_result = service.events().list(calendarId='primary', timeMin=now,
                                                  maxResults=1, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])
            
            if not events:
                next_meeting_title = "No meetings today"
                next_meeting_time = "Day off!"
            else:
                event = events[0]
                summary = event.get('summary', 'Untitled Meeting')
                start = event['start'].get('dateTime', event['start'].get('date'))
                
                next_meeting_title = summary
                
                if 'T' in start:
                    date_part, time_part = start.split('T')
                    time_str = time_part[:5]
                    
                    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
                    
                    if date_part == today_str:
                        next_meeting_time = f"Today {time_str}"
                    else:
                        event_date = datetime.datetime.strptime(date_part, '%Y-%m-%d')
                        day_name = event_date.strftime('%a')
                        next_meeting_time = f"{day_name} {time_str}"
                else:
                    next_meeting_time = "All day event"
                    
                next_meeting_title = summary
                
        except Exception as e:
            print(f"[ERROR] Calendar update failed: {e}")
            next_meeting_title = "Calendar Error"
            next_meeting_time = ""
            
        time.sleep(600)

def calculate_network_speed():
    """Calculates current upload and download speeds in Mbps"""
    global last_bytes_recv, last_bytes_sent, prev_network_time, mbps_download, mbps_upload
    
    current_time = time.time()
    dt = current_time - prev_network_time
    if dt < 0.1: return
    
    net_data = psutil.net_io_counters()
    
    bytes_download = net_data.bytes_recv - last_bytes_recv
    bytes_upload = net_data.bytes_sent - last_bytes_sent
    
    mbps_download = (bytes_download * 8) / (1024 * 1024) / dt
    mbps_upload = (bytes_upload * 8) / (1024 * 1024) / dt
    
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
            if name.startswith('en') or name.startswith('eth'):
                ethernet_ok = True
            elif name.startswith('wl'):
                wifi_ok = True
                
    if ethernet_ok:
        return "Cable (Ethernet)"
    elif wifi_ok:
        try:
            ssid = subprocess.check_output(["iwgetid", "-r"], text=True).strip()
            return f"Wi-Fi: {ssid}" if ssid else "Wi-Fi: Connected"
        except:
            return "Wi-Fi: Connected"
    return "Disconnected"

def get_cpu_temp():
    try:
        result = subprocess.check_output(["sensors"], text=True)
        match = re.search(r'Tctl:\s*\+([0-9.]+)', result)
        if match:
            return f"{int(float(match.group(1)))} oC"
    except Exception:
        pass
    return "N/A"

def get_gpu_temp():
    try:
        cmd = ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"]
        temp = subprocess.check_output(cmd, text=True).strip()
        return f"{temp} oC"
    except Exception:
        return "N/A"

def update_weather():
    global weather_data
    try:
        url = f"https://wttr.in/{CITY}?format=%t;%C;%h;%w"
        weather_resp = requests.get(url, timeout=3)
        if weather_resp.status_code == 200:
            data = weather_resp.text.split(";")
            weather_data["temperature"] = data[0].replace("+", "").replace("°C", "")
            weather_data["condition"] = get_simple_condition(data[1])
            weather_data["humidity"] = data[2]
            weather_data["wind_speed"] = data[3]
        else:
            print(f"update_weather: {weather_resp.status_code}")
    except Exception:
        pass

def weather_icon(condition):
    icons = {
        "Clear": "☀",
        "Cloudy": "☁",
        "Rainy": "☂",
        "Snow": "❄",
        "Thunderstorm": "⚡",
        "Overcast": "☁",
        "Unknown": ""
    }
    return icons.get(condition, condition)

def get_simple_condition(raw_cond):
    cond = raw_cond.lower().strip()
    if 'thunderstorm' in cond: return 'Thunderstorm'
    if 'rain' in cond: return 'Rainy'
    if 'cloud' or 'overcast' in cond: return 'Cloudy'
    if 'sun' in cond or 'clear' in cond: return 'Clear'
    return 'N/A'

def get_wind_direction_icon(direction):
    wind_map = {
    '↑': 'N', '↗': 'NE', '→': 'E', '↘': 'SE',
    '↓': 'S', '↙': 'SW', '←': 'W', '↖': 'NW'
    }
    return wind_map.get(direction, '?')

# --- SCREEN 0: GIANT CLOCK ---
def screen_clock(draw):
    actual_time = datetime.datetime.now().strftime("%H:%M:%S")
    draw.text((0, 0), actual_time, font=font_large, fill=255)
    draw.text((0, 20), f"Temp: {weather_data['temperature']} °C", font=font_small, fill=255)
    
    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌", font=font_small, fill=255)
# --- SCREEN 1: WEATHER ---
def weather_screen(draw):
    draw.text((0, 0), f"{weather_data['temperature']}°C", font=font_large, fill=255)
    draw.text((85, 0), f"{weather_icon(weather_data['condition'])}", font=font_icon, fill=255)
    draw.text((85, 22), f"H: {weather_data['humidity']}", font=font_small, fill=255)    
    draw.text((0, 22), f"W: {weather_data['wind_speed'][1:].replace('km/h', '')} {get_wind_direction_icon(weather_data['wind_speed'][0])}", font=font_small, fill=255)
    
    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌" , font=font_small, fill=255)

# --- SCREEN 2: PC PERFORMANCE ---
def screen_performance(draw):
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

    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌" , font=font_small, fill=255)

# --- SCREEN 3: PC INTERNAL SENSORS ---
def screen_sensors(draw):
    internal_temp = get_cpu_temp()
    gpu_temp = get_gpu_temp()
    draw.text((0, 0), "HARDWARE SENSORS:", font=font_small, fill=255)
    draw.text((0, 12), f"CPU Temp: {internal_temp.split()[0]} °C", font=font_small, fill=255)
    draw.text((0, 22), f"GPU Temp: {gpu_temp.split()[0]} °C", font=font_small, fill=255)

    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌" , font=font_small, fill=255)

# --- SCREEN 4: LOCAL NETWORK STATUS ---
def screen_network(draw):
    net_status = get_network_status()
    draw.text((0, 0), "LOCAL NETWORK:", font=font_small, fill=255)
    draw.text((0, 15), net_status, font=font_small, fill=255)

    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌" , font=font_small, fill=255)

# --- SCREEN 5: REAL-TIME NETWORK TRAFFIC ---
def screen_nettraffic(draw):
    draw.text((0, 0), "NET TRAFFIC:", font=font_small, fill=255)
    draw.text((0, 12), f"Down: {mbps_download:.1f} Mbps", font=font_small, fill=255)
    draw.text((0, 22), f"Up:   {mbps_upload:.1f} Mbps", font=font_small, fill=255)

    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌" , font=font_small, fill=255)

# --- SCREEN 6: NEXT MEETING ---
def screen_calendar(draw):
    global scroll_x
    draw.text((0, 0), "NEXT MEETING:", font=font_small, fill=255)
    full_text = f"{next_meeting_title} - {next_meeting_time}"
    text_width = font_small.getlength(full_text)
    display_width = 128
    draw.text((scroll_x, 16), full_text, font=font_small, fill=255)

    if text_width > display_width:
        scroll_x -= 4
        if scroll_x < -text_width:
            scroll_x = display_width
    else:
        scroll_x = 0

    if shared_state["manual_mode"]:
        draw.text((120, 0), "📌" , font=font_small, fill=255)

screens = [
    {"name": "clock", "draw": screen_clock, "timeout": 6, "enabled": True},
    {"name": "weather", "draw": weather_screen, "timeout": 3, "enabled": True},
    {"name": "performance", "draw": screen_performance, "timeout": 3, "enabled": False},
    {"name": "sensors", "draw": screen_sensors, "timeout": 3, "enabled": False},
    {"name": "network", "draw": screen_network, "timeout": 3, "enabled": False},
    {"name": "net-traffic", "draw": screen_nettraffic, "timeout": 3, "enabled": False},
    {"name": "calendar", "draw": screen_calendar, "timeout": 8, "enabled": True}
]

active_screens = [s for s in screens if s["enabled"]]
current_index = 0
scroll_x = 0
current_screen = 0
typing_counter = 0

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    load_status()
    
    #--- You can choose  what SPLASH screen you want to use
    # boot_animation(draw)
    show_splash()
    # ---

    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)

    if os.path.exists(credentials_path):
        threading.Thread(target=update_calendar_loop, daemon=True).start()
    else:
        print("[WARNING] credentials.json not found. Calendar screen will be skipped.")

    active_screens = [s for s in screens if s["enabled"]]
    update_weather()

    while True:
        if shared_state["manual_mode"]:
            target = next((s for s in screens if s["name"] == shared_state["target_screen"]), None)
            current_screen_cfg = target if target else screens[0]
        else:
            try:
                active_screens = [s for s in screens if s["enabled"]]
                # print(f"Active screens: {[s['name'] for s in active_screens]}")
                if not active_screens:
                    time.sleep(1)
                    continue
            except Exception as e:
                
                print(f"[ERROR] AUTO MODE:Failed to get active screens: {e}")
                continue

            try:
                if time.time() - shared_state["last_screen_change"] > active_screens[current_index]["timeout"]:
                    update_weather()                    
                    last_network_update = time.time()
                    current_index = (current_index + 1) % len(active_screens)
                    shared_state["last_screen_change"] = time.time()
                
            except Exception as e:
                print(f"[ERROR] TIME: Failed to update screen: {e}")
                # print(f"active_screens: {[s['name'] for s in active_screens]}, current_index: {current_index}")
                current_index = (current_index + 1) % len(active_screens)
                shared_state["last_screen_change"] = time.time()
                time.sleep(1)
                continue
            calculate_network_speed()

            current_screen_cfg = active_screens[current_index]

        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        current_screen_cfg["draw"](draw)
        oled.image(image)
        oled.show()
        
        time.sleep(0.1)