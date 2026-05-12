#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── WiFi Credentials ─────────────────────────────
const char* ssid       = "YOUR_WIFI_SSID";           // Your WiFi name
const char* password   = "YOUR_WIFI_PASSWORD";      // Your WiFi password

// ── Flask Server URL ─────────────────────────────
const char* serverUrl  = "http://<YOUR_PC_IP>:5000/api/sensor-data";

// ── Sensor Pin & Calibration ─────────────────────
const int sensorPin   = 34;
int lastState         = HIGH;         // ← from your working code
int particleCount     = 0;            // ← from your working code
unsigned long lastEventTime = 0;      // ← from your working code
unsigned long debounceMs    = 50;     // ← from your working code

// ═══════════════════════════════════════════════
//  TIMING
// ═══════════════════════════════════════════════
unsigned long lastSend       = 0;
unsigned long lastWifiCheck  = 0;
const long sendInterval      = 2000;
const long wifiCheckInterval = 5000;

bool serverReachable = false;

// ═══════════════════════════════════════════════
//  WiFi Connect
// ═══════════════════════════════════════════════
void connectWiFi() {
  Serial.printf("\nConnecting to WiFi: %s ", ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi Connected!");
    Serial.println("  IP     : " + WiFi.localIP().toString());
    Serial.println("  Signal : " + String(WiFi.RSSI()) + " dBm");
    Serial.println("  Server : " + String(serverUrl));
  } else {
    Serial.println("\n✗ WiFi FAILED — running offline.");
  }
}

// ═══════════════════════════════════════════════
//  POST to Flask
// ═══════════════════════════════════════════════
bool postToFlask(int count, String state) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(3000);

  JsonDocument doc;
  doc["count"] = count;
  doc["state"] = state;

  String json;
  serializeJson(doc, json);

  int httpCode = http.POST(json);
  http.end();

  if (httpCode == 200) {
    serverReachable = true;
    return true;
  } else if (httpCode == -1) {
    Serial.println("  ✗ Server unreachable — is Flask running?");
    serverReachable = false;
    return false;
  } else {
    Serial.printf("  ✗ HTTP Error: %d\n", httpCode);
    serverReachable = false;
    return false;
  }
}

// ═══════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  pinMode(sensorPin, INPUT);   // ← exact from your working code
  delay(2000);

  Serial.println("\n========================================");
  Serial.println("  MICROPLASTICS DETECTION SYSTEM");
  Serial.println("========================================");
  connectWiFi();
  Serial.println("\n[Ready — streaming sensor data...]\n");
}

// ═══════════════════════════════════════════════
//  LOOP — sensor logic is IDENTICAL to your
// ═══════════════════════════════════════════════
void loop() {
  int currentState = digitalRead(sensorPin);

  // ── EXACT logic from your working code ──────
  if (lastState == HIGH && currentState == LOW) {
    if (millis() - lastEventTime > debounceMs) {
      particleCount++;
      lastEventTime = millis();
      Serial.print("PARTICLE DETECTED. Count = ");
      Serial.println(particleCount);
    }
  }

  lastState = currentState;

  // ── EXACT serial output from your working code
  if (currentState == HIGH) {
    Serial.println("STATE: CLEAR");
  } else {
    Serial.println("STATE: PARTICLE PRESENT");
  }

  // ── WiFi reconnect check ─────────────────────
  if (millis() - lastWifiCheck > wifiCheckInterval) {
    lastWifiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("⚠ WiFi lost — reconnecting...");
      WiFi.reconnect();
    }
  }

  // ── POST to Flask every 2 seconds ───────────
  if (millis() - lastSend > sendInterval) {
    lastSend = millis();
    String stateStr = (currentState == HIGH) ? "CLEAR" : "PARTICLE PRESENT";
    bool sent = postToFlask(particleCount, stateStr);
    if (sent) {
      Serial.printf("  ✓ Sent → Count:%d | State:%s\n",
                    particleCount, stateStr.c_str());
    }
  }

  delay(100);  // ← exact from your working code
}
