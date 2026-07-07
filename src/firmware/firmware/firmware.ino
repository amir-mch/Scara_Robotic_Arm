// =============================================================================
// SCARA Robot Firmware — Arduino IDE (ESP32 + micro-ROS)
// Modularized Architecture — setup() and loop() main entrypoints
// =============================================================================

#include <Arduino.h>
#include <micro_ros_arduino.h>
#include "kinematics_engine.h"
#include "stepper_core.h"
#include "ros_comms.h"
#include "automation_core.h"
#include "homing_module.h"

void setup() {
  Serial.begin(115200);
  
  // Set up transport channel for micro-ROS
  set_microros_transports();
  
  // Initialize multi-status feedback LED
  init_automation_led();

  // Initialize status heartbeat pin
  pinMode(ACTIVITY_LED_PIN, OUTPUT);
  digitalWrite(ACTIVITY_LED_PIN, LOW);

  // Initialize Steppers and hardware timers
  init_steppers();

  // Initialize Safe Homing Module
  initHomingSystem();

  // Initialize ROS Node Comms
  init_ros_comms();
}

void loop() {
  // 1. Process ROS 2 subscriptions, spin executor, and feedback publishers
  spin_ros_comms();

  // 1.5. Execute homing sequence if requested (outside executor callback context)
  if (homing_requested) {
    homing_requested = false;
    runHomingSequence();
  }

  // 2. Dequeue streamed velocities from playout buffer
  static unsigned long last_dequeue = 0;
  if (velocity_mode && millis() - last_dequeue >= 30) {
    last_dequeue = millis();
    VelocityCmd cmd;
    portENTER_CRITICAL(&stepperMux);
    if (dequeue_velocity(cmd)) {
      target_vel_x = cmd.vx;
      target_vel_y = cmd.vy;
      target_vel_z = cmd.vz;
    } else {
      if (millis() - last_vel_received_time > 150) {
        target_vel_x = 0.0f;
        target_vel_y = 0.0f;
        target_vel_z = 0.0f;
      }
    }
    portEXIT_CRITICAL(&stepperMux);
  }

  // 3. Process S-curve acceleration updates (float calculations outside locks)
  update_stepper_ramps();

  // 4. Update multi-status visual LED indicators
  update_automation_led(current_status, emergency_hit);

  // 5. Activity Heartbeat (1Hz blink on Pin 4)
  static unsigned long last_led = 0;
  if (millis() - last_led >= 500) {
    last_led = millis();
    digitalWrite(ACTIVITY_LED_PIN, !digitalRead(ACTIVITY_LED_PIN));
  }

  delay(1); // Yield CPU to FreeRTOS background serialization tasks to prevent WDT resets
}
