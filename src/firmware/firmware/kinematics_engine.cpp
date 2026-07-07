#include "kinematics_engine.h"

// Pin Definitions
const int STEP_X_PIN = 25;
const int DIR_X_PIN = 26;
const int STEP_Y_PIN = 27;
const int DIR_Y_PIN = 14;
const int STEP_Z_PIN = 16;
const int DIR_Z_PIN = 17;
const int SHIELD_EN_PIN = 5;

// Swapped pin assignments to correct servo assignment inversion (Bug Fix 1):
// - Servo 1 (Wrist Angle) -> Pin 19
// - Servo 2 (Gripper Open/Close Intensity) -> Pin 18
const int SERVO_1_PIN = 19;
const int SERVO_2_PIN = 18;

const int LIMIT_X_PIN = 22;
const int LIMIT_Y_PIN = 21;
const int LIMIT_Z_PIN = 23;

const int DEBUG_LED_PIN = 2;
const int ACTIVITY_LED_PIN = 4;

// Calibration Constants
const float STEPS_PER_DEGREE_X = 47.058f;
const float STEPS_PER_DEGREE_Y = 585.83f;
const float STEPS_PER_MM_Z = 10.0f;

// Homing Direction Signs and Speeds
const int DIR_X_HOMING = -1;
const int DIR_Y_HOMING = 1;
const int DIR_Z_HOMING = 1;
const float HOMING_FAST_X = 1200.0f;
const float HOMING_FAST_Y = 8000.0f;
const float HOMING_FAST_Z = 3000.0f;
const float HOMING_SLOW_X = 300.0f;
const float HOMING_SLOW_Y = 1000.0f;
const float HOMING_SLOW_Z = 800.0f;
const float HOMING_BACKOFF_X = 500.0f;
const float HOMING_BACKOFF_Y = 2000.0f;
const float HOMING_BACKOFF_Z = 1200.0f;

long degrees_to_steps_x(float deg) {
  return lround(deg * STEPS_PER_DEGREE_X);
}

long degrees_to_steps_y(float deg) {
  return lround(deg * STEPS_PER_DEGREE_Y);
}

long mm_to_steps_z(float mm) {
  return lround(mm * STEPS_PER_MM_Z);
}
