#ifndef KINEMATICS_ENGINE_H
#define KINEMATICS_ENGINE_H

#include <Arduino.h>

// Pin Definitions
extern const int STEP_X_PIN;
extern const int DIR_X_PIN;
extern const int STEP_Y_PIN;
extern const int DIR_Y_PIN;
extern const int STEP_Z_PIN;
extern const int DIR_Z_PIN;
extern const int SHIELD_EN_PIN;

extern const int SERVO_1_PIN;
extern const int SERVO_2_PIN;

extern const int LIMIT_X_PIN;
extern const int LIMIT_Y_PIN;
extern const int LIMIT_Z_PIN;

extern const int DEBUG_LED_PIN;
extern const int ACTIVITY_LED_PIN;

// Calibration Constants
extern const float STEPS_PER_DEGREE_X;
extern const float STEPS_PER_DEGREE_Y;
extern const float STEPS_PER_MM_Z;

// Homing Directions & Speeds
extern const int DIR_X_HOMING;
extern const int DIR_Y_HOMING;
extern const int DIR_Z_HOMING;
extern const float HOMING_FAST_X;
extern const float HOMING_FAST_Y;
extern const float HOMING_FAST_Z;
extern const float HOMING_SLOW_X;
extern const float HOMING_SLOW_Y;
extern const float HOMING_SLOW_Z;
extern const float HOMING_BACKOFF_X;
extern const float HOMING_BACKOFF_Y;
extern const float HOMING_BACKOFF_Z;

long degrees_to_steps_x(float deg);
long degrees_to_steps_y(float deg);
long mm_to_steps_z(float mm);

#endif // KINEMATICS_ENGINE_H
