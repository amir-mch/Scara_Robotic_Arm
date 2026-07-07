#include "stepper_core.h"
#include "kinematics_engine.h"
#include "ros_comms.h"
#include "automation_core.h"
#include "esp_timer.h"

// Instantiate AccelStepper and Servo objects
AccelStepper stepperX(AccelStepper::DRIVER, STEP_X_PIN, DIR_X_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_Y_PIN, DIR_Y_PIN);
AccelStepper stepperZ(AccelStepper::DRIVER, STEP_Z_PIN, DIR_Z_PIN);

Servo servo1;
Servo servo2;

portMUX_TYPE stepperMux = portMUX_INITIALIZER_UNLOCKED;

// Playout buffer implementation
volatile VelocityCmd vel_queue[VEL_QUEUE_SIZE];
volatile int vel_queue_head = 0;
volatile int vel_queue_tail = 0;
volatile unsigned long last_vel_received_time = 0;

volatile bool stepping_enabled = false;
volatile bool emergency_hit = false;
volatile bool velocity_mode = false;

// Global motion variables
float target_vel_x = 0.0f;
float target_vel_y = 0.0f;
float target_vel_z = 0.0f;
float current_vel_x = 0.0f;
float current_vel_y = 0.0f;
float current_vel_z = 0.0f;
float current_accel_x = 0.0f;
float current_accel_y = 0.0f;
float current_accel_z = 0.0f;

float target_x = 0.0f;
float target_y = 0.0f;
float target_z = 0.0f;

float max_speed_x = 4000.0f;
float accel_x = 2000.0f;
float max_speed_y = 20000.0f;
float accel_y = 10000.0f;
float max_speed_z = 1000.0f;
float accel_z = 500.0f;

String current_status = "IDLE";
String last_command = "NONE";
int motor_enabled = 1;

esp_timer_handle_t stepTimer = NULL;
volatile uint64_t step_interval_us = 25; // 40 kHz frequency

// Playout Queue Management Helpers
bool enqueue_velocity(float vx, float vy, float vz) {
  int next_head = (vel_queue_head + 1) % VEL_QUEUE_SIZE;
  if (next_head == vel_queue_tail) {
    return false; // Full
  }
  vel_queue[vel_queue_head].vx = vx;
  vel_queue[vel_queue_head].vy = vy;
  vel_queue[vel_queue_head].vz = vz;
  vel_queue_head = next_head;
  last_vel_received_time = millis();
  return true;
}

bool dequeue_velocity(VelocityCmd &cmd) {
  if (vel_queue_head == vel_queue_tail) {
    return false; // Empty
  }
  cmd.vx = vel_queue[vel_queue_tail].vx;
  cmd.vy = vel_queue[vel_queue_tail].vy;
  cmd.vz = vel_queue[vel_queue_tail].vz;
  vel_queue_tail = (vel_queue_tail + 1) % VEL_QUEUE_SIZE;
  return true;
}

void clear_velocity_queue() {
  vel_queue_head = 0;
  vel_queue_tail = 0;
}

// STEP TIMER Callback (runs periodically on Core 0)
void IRAM_ATTR onStepTimer(void *arg) {
  if (!stepping_enabled || emergency_hit)
    return;

  portENTER_CRITICAL(&stepperMux);

  // ── Limit Switch Safety ──
  if (digitalRead(LIMIT_X_PIN) == LOW) {
    bool moving_into_limit =
        velocity_mode
            ? (stepperX.speed() * DIR_X_HOMING > 0)
            : ((stepperX.targetPosition() - stepperX.currentPosition()) *
                   DIR_X_HOMING >
               0);
    if (moving_into_limit) {
      stepperX.setSpeed(0);
      if (!velocity_mode)
        stepperX.moveTo(stepperX.currentPosition());
    }
  }
  if (digitalRead(LIMIT_Y_PIN) == LOW) {
    bool moving_into_limit =
        velocity_mode
            ? (stepperY.speed() * DIR_Y_HOMING > 0)
            : ((stepperY.targetPosition() - stepperY.currentPosition()) *
                   DIR_Y_HOMING >
               0);
    if (moving_into_limit) {
      stepperY.setSpeed(0);
      if (!velocity_mode)
        stepperY.moveTo(stepperY.currentPosition());
    }
  }
  if (digitalRead(LIMIT_Z_PIN) == LOW) {
    bool moving_into_limit =
        velocity_mode
            ? (stepperZ.speed() * DIR_Z_HOMING > 0)
            : ((stepperZ.targetPosition() - stepperZ.currentPosition()) *
                   DIR_Z_HOMING >
               0);
    if (moving_into_limit) {
      stepperZ.setSpeed(0);
      if (!velocity_mode)
        stepperZ.moveTo(stepperZ.currentPosition());
    }
  }

  // ── Step the motors ──
  if (velocity_mode) {
    stepperX.runSpeed();
    stepperY.runSpeed();
    stepperZ.runSpeed();
  } else {
    stepperX.run();
    stepperY.run();
    stepperZ.run();
  }

  portEXIT_CRITICAL(&stepperMux);
}

void init_steppers() {
  pinMode(SHIELD_EN_PIN, OUTPUT);
  pinMode(LIMIT_X_PIN, INPUT_PULLUP);
  pinMode(LIMIT_Y_PIN, INPUT_PULLUP);
  pinMode(LIMIT_Z_PIN, INPUT_PULLUP);

  set_motor_state(1);

  stepperX.setMaxSpeed(max_speed_x);
  stepperX.setAcceleration(accel_x);
  stepperY.setMaxSpeed(max_speed_y);
  stepperY.setAcceleration(accel_y);
  stepperZ.setMaxSpeed(max_speed_z);
  stepperZ.setAcceleration(accel_z);

  servo1.setPeriodHertz(50);
  servo1.attach(SERVO_1_PIN, 500, 2400);
  servo2.setPeriodHertz(50);
  servo2.attach(SERVO_2_PIN, 500, 2400);

  // High-Resolution timer setup
  const esp_timer_create_args_t timer_args = {
      .callback = &onStepTimer,
      .arg = NULL,
      .dispatch_method = ESP_TIMER_TASK,
      .name = "step_timer"
  };
  esp_timer_create(&timer_args, &stepTimer);
  esp_timer_start_periodic(stepTimer, step_interval_us);
  stepping_enabled = true;
}

void pause_stepping_timer() {
  stepping_enabled = false;
  if (stepTimer) {
    esp_timer_stop(stepTimer);
  }
}

void resume_stepping_timer() {
  if (stepTimer) {
    esp_timer_stop(stepTimer);
    esp_timer_start_periodic(stepTimer, step_interval_us);
  }
  stepping_enabled = true;
}

void set_motor_state(int enable) {
  motor_enabled = enable;
  if (enable) {
    digitalWrite(SHIELD_EN_PIN, LOW); // LOW enables shield
  } else {
    digitalWrite(SHIELD_EN_PIN, HIGH);
    stepping_enabled = false;
  }
}



// S-curve Ramping Updates — Optimized to perform floating-point math OUTSIDE critical locks (Bug Fix 3)
void update_stepper_ramps() {
  static unsigned long last_ramp = 0;
  if (!velocity_mode) {
    last_ramp = 0;
    return;
  }

  if (last_ramp == 0)
    last_ramp = millis();
  unsigned long now = millis();
  if (now - last_ramp >= 10) {
    float dt = (now - last_ramp) / 1000.0f;
    last_ramp = now;

    // 1. Copy shared targets under lightweight lock
    portENTER_CRITICAL(&stepperMux);
    float t_vx = target_vel_x;
    float t_vy = target_vel_y;
    float t_vz = target_vel_z;
    portEXIT_CRITICAL(&stepperMux);

    // 2. Perform all floating point S-curve math OUTSIDE the critical section
    float max_jerk_x = 5.0f * accel_x;
    float step_jerk_x = max_jerk_x * dt;
    float target_accel_x = (t_vx - current_vel_x) * 15.0f;
    target_accel_x = constrain(target_accel_x, -accel_x, accel_x);
    float jerk_x = target_accel_x - current_accel_x;
    jerk_x = constrain(jerk_x, -step_jerk_x, step_jerk_x);
    current_accel_x += jerk_x;
    current_vel_x += current_accel_x * dt;

    float max_jerk_y = 5.0f * accel_y;
    float step_jerk_y = max_jerk_y * dt;
    float target_accel_y = (t_vy - current_vel_y) * 15.0f;
    target_accel_y = constrain(target_accel_y, -accel_y, accel_y);
    float jerk_y = target_accel_y - current_accel_y;
    jerk_y = constrain(jerk_y, -step_jerk_y, step_jerk_y);
    current_accel_y += jerk_y;
    current_vel_y += current_accel_y * dt;

    float max_jerk_z = 5.0f * accel_z;
    float step_jerk_z = max_jerk_z * dt;
    float target_accel_z = (t_vz - current_vel_z) * 15.0f;
    target_accel_z = constrain(target_accel_z, -accel_z, accel_z);
    float jerk_z = target_accel_z - current_accel_z;
    jerk_z = constrain(jerk_z, -step_jerk_z, step_jerk_z);
    current_accel_z += jerk_z;
    current_vel_z += current_accel_z * dt;

    // 3. Write calculated speeds and finalize stepper states under lightweight lock
    portENTER_CRITICAL(&stepperMux);
    stepperX.setSpeed(current_vel_x);
    stepperY.setSpeed(current_vel_y);
    stepperZ.setSpeed(current_vel_z);

    // If target is zero and we reached it, disable stepping to save CPU
    if (fabs(t_vx) < 0.1f && fabs(t_vy) < 0.1f &&
        fabs(t_vz) < 0.1f && fabs(current_vel_x) < 0.1f &&
        fabs(current_vel_y) < 0.1f && fabs(current_vel_z) < 0.1f) {
      velocity_mode = false;
      stepping_enabled = false;
      current_vel_x = 0.0f;
      current_accel_x = 0.0f;
      current_vel_y = 0.0f;
      current_accel_y = 0.0f;
      current_vel_z = 0.0f;
      current_accel_z = 0.0f;
      
      // Synchronize internal stepper target with final jog position
      stepperX.moveTo(stepperX.currentPosition());
      stepperY.moveTo(stepperY.currentPosition());
      stepperZ.moveTo(stepperZ.currentPosition());

      // Update target variables for GUI feedback alignment
      target_x = (float)stepperX.currentPosition() / STEPS_PER_DEGREE_X;
      target_y = (float)stepperY.currentPosition() / STEPS_PER_DEGREE_Y;
      target_z = (float)stepperZ.currentPosition() / STEPS_PER_MM_Z;
    }
    portEXIT_CRITICAL(&stepperMux);
  }
}
