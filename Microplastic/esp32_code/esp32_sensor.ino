#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── WiFi Credentials ─────────────────────────────
const char* ssid     = "Realme 11 Pro+ 5G";      // ← Edit
const char* password = "11092005";  // ← Edit

// ── Flask Server URL ─────────────────────────────
const char* serverUrl = "http://192.168.0.101:5000/data";  // ← Edit PC IP

// ── Sensor Pin & Calibration ─────────────────────
const int sensorPin = 34;
const int clearRef  = 3200;   // Clear water reading
const int dirtyRef  = 1200;   // Dirty water reading

// ── Timers ────────────────────────────────────────
unsigned long lastPrint = 0;
unsigned long lastSend  = 0;
int readingCount = 0;

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n=== MICROPLASTICS SENSOR READY ===");
  Serial.println("LDR GPIO34 | Laser manual ON");
  Serial.printf("Calib: Clear=%d | Dirty=%d\n", clearRef, dirtyRef);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✓ WiFi Connected: " + WiFi.localIP().toString());
}

void loop() {

  // ── Print to Serial every 500ms ──────────────────
  if (millis() - lastPrint > 500) {
    lastPrint = millis();

    int raw = analogRead(sensorPin);
    int particles = constrain(map(raw, dirtyRef, clearRef, 150, 5), 0, 200);
    int size_um   = constrain(map(raw, dirtyRef, clearRef, 90, 15), 5, 100);

    String status;
    if      (raw >= 2600) status = "CLEAN";
    else if (raw >= 2000) status = "LOW";
    else if (raw >= 1500) status = "MODERATE";
    else                  status = "HIGH";

    Serial.printf("| Raw:%4d | P:%3d | Size:%2dμm | %s |\n",
                  raw, particles, size_um, status.c_str());

    readingCount++;
    if (readingCount % 4 == 0) {
      Serial.println("-----------------------------");
    }
  }

  // ── Send to Flask every 2 seconds ────────────────
  if (millis() - lastSend > 2000) {
    lastSend = millis();

    int raw = analogRead(sensorPin);
    int particles = constrain(map(raw, dirtyRef, clearRef, 150, 5), 0, 200);
    int size_um   = constrain(map(raw, dirtyRef, clearRef, 90, 15), 5, 100);

    String status;
    if      (raw >= 2600) status = "Good";
    else if (raw >= 2000) status = "Moderate";
    else if (raw >= 1500) status = "Moderate";
    else                  status = "Contaminated";

    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(serverUrl);
      http.addHeader("Content-Type", "application/json");

      StaticJsonDocument<200> doc;
      doc["raw_adc"]   = raw;
      doc["particles"] = particles;
      doc["size"]      = size_um;
      doc["status"]    = status;

      String json;
      serializeJson(doc, json);

      int code = http.POST(json);
      if (code == 200) Serial.println("  ✓ Dashboard updated");
      else             Serial.printf("  ✗ HTTP Error: %d\n", code);

      http.end();
    } else {
      Serial.println("  ✗ WiFi disconnected — retrying...");
      WiFi.reconnect();
    }
  }
}