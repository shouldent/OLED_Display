# My PC & Network Live Monitor (Adafruit OLED + FT232H)

A real-time hardware and network traffic monitor for Linux, designed to run on an SSD1306 OLED display (128x32) connected via USB using the Adafruit FT232H breakout (Blinka).

## Features
* **Digital Clock:** Large, easy-to-read time format.
* **System Performance:** Dynamic progress bars for CPU and RAM usage.
* **Hardware Sensors:** Real-time CPU temperature (`Tctl`) and system uptime.
* **Local Network Status:** Auto-detects active connections (Ethernet or Wi-Fi with SSID).
* **Live Network Traffic:** Real-time download and upload speed measured locally in Mbps.

## Hardware Requirements
* SSD1306 I2C OLED Display (128x32)
* Adafruit FT232H Breakout (or MCP2221 with minor variable adjustments)
* Jumper wires

_Note: I will be adding new features like a 3D Printed box to mount it under the PC monitor_


## Installation & Setup

### 1. Clone the repository and set up the environment
```bash
git clone https://github.com/shouldent/OLED_Display.git
cd OLED_Display

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure the Linux Service (Systemd)

To make the monitor start automatically on boot, create a systemd service file:
```bash
sudo nano /etc/systemd/system/oled.service
```
Paste the following configuration (make sure to replace *your_username* with your actual Linux username):
```ini
[Unit]
Description=OLED Display Monitor
After=network.target

[Service]
User=your_username
Environment=BLINKA_FT232H=1
WorkingDirectory=/home/your_username/OLED_Display
ExecStart=/home/your_username/OLED_Display/venv/bin/python3 /home/your_username/OLED_Display/OLED_full.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
### 3. Enable and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable oled.service
sudo systemctl start oled.service
```
The script includes a hotfix at the beginning to bypass a known Blinka/Microcontroller initialization bug present in Python 3.12+ environments.

Make sure to drop your preferred .ttf font file into the project root directory and rename it to fuente_reloj.ttf.

## 4. Google Calendar Integration (Optional)
To enable the next meeting display on screen 5:
1. Go to the Google Cloud Console and enable the Google Calendar API.
2. Download your `credentials.json` file.
3. Place `credentials.json` in the root directory of this project.
4. Run the script; it will prompt you to authenticate via browser on the first run.