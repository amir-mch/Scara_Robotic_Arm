#ifndef STEPPER_CORE_H
#define STEPPER_CORE_H

#include <AccelStepper.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include "esp_timer.h"

extern AccelStepper stepperX;
extern AccelStepper stepperY;
extern AccelStepper stepperZ;
extern portMUX_TYPE stepperMux;

extern Servo servo1;
extern Servo servo2;

// Playout buffer struct
struct VelocityCmd {
  float vx;
  float vy;
  float vz;
};

#define VEL_QUEUE_SIZE 8
extern volatile VelocityCmd vel_queue[VEL_QUEUE_SIZE];
extern volatile int vel_queue_head;
extern volatile int vel_queue_tail;
extern volatile unsigned long last_vel_received_time;

extern volatile bool stepping_enabled;
extern volatile bool emergency_hit;
extern volatile bool velocity_mode;

extern float target_vel_x;
extern float target_vel_y;
extern float target_vel_z;
extern float current_vel_x;
extern float current_vel_y;
extern float current_vel_z;
extern float current_accel_x;
extern float current_accel_y;
extern float current_accel_z;

extern float target_x;
extern float target_y;
extern float target_z;

extern float max_speed_x;
extern float accel_x;
extern float max_speed_y;
extern float accel_y;
extern float max_speed_z;
extern float accel_z;

extern String current_status;
extern String last_command;
extern int motor_enabled;

extern esp_timer_handle_t stepTimer;
extern volatile uint64_t step_interval_us;

void init_steppers();
void pause_stepping_timer();
void resume_stepping_timer();
void update_stepper_ramps();
void set_motor_state(int enable);

bool enqueue_velocity(float vx, float vy, float vz);
bool dequeue_velocity(VelocityCmd &cmd);
void clear_velocity_queue();

#endif // STEPPER_CORE_H
