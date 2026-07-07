#ifndef AUTOMATION_CORE_H
#define AUTOMATION_CORE_H

#include <Arduino.h>

// Onboard LED Pin configuration
static const int STATUS_LED_PIN = 2; // GPIO 2

static void init_automation_led() {
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);
}

static void update_automation_led(const String& current_status, bool emergency_hit) {
  static unsigned long last_status_led = 0;
  static bool status_led_state = false;

  if (emergency_hit) {
    digitalWrite(STATUS_LED_PIN, LOW); // Hard power-down condition (Solid OFF)
  } else if (current_status == "ACTION") {
    // Action State: flash rapidly (10Hz -> toggle every 50ms)
    if (millis() - last_status_led >= 50) {
      last_status_led = millis();
      status_led_state = !status_led_state;
      digitalWrite(STATUS_LED_PIN, status_led_state ? HIGH : LOW);
    }
  } else if (current_status == "MOVING" || current_status == "HOMING") {
    digitalWrite(STATUS_LED_PIN, HIGH); // Solid ON during active hazardous motion
  } else {
    // IDLE State: blink at slow rate (1Hz -> toggle every 500ms)
    if (millis() - last_status_led >= 500) {
      last_status_led = millis();
      status_led_state = !status_led_state;
      digitalWrite(STATUS_LED_PIN, status_led_state ? HIGH : LOW);
    }
  }
}

#endif // AUTOMATION_CORE_H
