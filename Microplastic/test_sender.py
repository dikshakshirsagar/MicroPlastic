"""
Test Data Sender — Simulates ESP32
===================================
Run this to test the dashboard without hardware.

Usage: python test_sender.py
"""

import requests
import random
import time

SERVER_URL = "http://localhost:5000/data"

print("=" * 45)
print("  µPlastic Test Sender (Simulating ESP32)")
print("  Sending to:", SERVER_URL)
print("=" * 45)

count = 0

while True:
    count += 1
    particles = random.randint(10, 150)
    size = random.randint(5, 80)

    if particles > 100:
        status = "Contaminated"
    elif particles > 50:
        status = "Moderate"
    else:
        status = "Good"

    payload = {
        "particles": particles,
        "size": size,
        "status": status
    }

    try:
        response = requests.post(SERVER_URL, json=payload)
        print(f"[{count:04d}]  Particles: {particles:3d}  |  Size: {size:2d}µm  |  "
              f"Status: {status:<13s}  |  Server: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[{count:04d}]  ✗ Cannot connect to server — is app.py running?")

    time.sleep(2)
