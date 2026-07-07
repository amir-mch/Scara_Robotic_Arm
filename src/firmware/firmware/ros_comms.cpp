#include "ros_comms.h"
#include "stepper_core.h"
#include "kinematics_engine.h"
#include "automation_core.h"
#include "homing_module.h"
#include <micro_ros_arduino.h>
#include <rcl/error_handling.h>
#include <rcl/rcl.h>
#include <rclc/executor.h>
#include <rclc/rclc.h>
#include <std_msgs/msg/float32_multi_array.h>
#include <std_msgs/msg/string.h>
#include <geometry_msgs/msg/point.h>

// micro-ROS Objects
rcl_allocator_t allocator;
rclc_support_t support;
rcl_node_t node;
rclc_executor_t executor;

// Subscriptions
rcl_subscription_t sub_target_pos;
rcl_subscription_t sub_cmd_vel;
rcl_subscription_t sub_command;
rcl_subscription_t sub_servo_control;
rcl_subscription_t sub_config;

// Publishers
rcl_publisher_t pub_feedback;
rcl_publisher_t pub_curr_pos;
rcl_publisher_t pub_homing_status;

// Message buffers
geometry_msgs__msg__Point msg_sub_target;
geometry_msgs__msg__Point msg_sub_vel;
std_msgs__msg__String msg_sub_command;
std_msgs__msg__Float32MultiArray msg_sub_servo;
std_msgs__msg__Float32MultiArray msg_sub_config;

std_msgs__msg__String msg_pub_feedback;
geometry_msgs__msg__Point msg_pub_curr_pos;
std_msgs__msg__String msg_pub_homing;

// Static character buffers
char buf_sub_command[64];
char buf_pub_feedback[192];
char buf_pub_homing[30];
float buf_sub_servo_data[2];
float config_buffer[6];

// Error check macros
#define RCCHECK(fn)                                                            \
  {                                                                            \
    rcl_ret_t rc = fn;                                                         \
    if (rc != RCL_RET_OK) {                                                    \
      while (1) {                                                              \
        digitalWrite(DEBUG_LED_PIN, !digitalRead(DEBUG_LED_PIN));              \
        delay(100);                                                            \
      }                                                                        \
    }                                                                          \
  }
#define RCSOFTCHECK(fn)                                                        \
  {                                                                            \
    rcl_ret_t rc = fn;                                                         \
    (void)rc;                                                                  \
  }

void publish_string_msg(rcl_publisher_t *pub, std_msgs__msg__String *msg,
                        const char *text) {
  snprintf(msg->data.data, msg->data.capacity, "%s", text);
  msg->data.size = strlen(msg->data.data);
  RCSOFTCHECK(rcl_publish(pub, msg, NULL));
}

// Target Position Callback
void callback_target_position(const void *msgin) {
  if (current_status == "HOMING")
    return;
  const geometry_msgs__msg__Point *msg =
      (const geometry_msgs__msg__Point *)msgin;
  last_command = "TARGET_POS";

  // Wrap negative shoulder angle target in [-180, 180] to positive range [0, 360]
  float input_angle_x = msg->x;
  if (input_angle_x < 0.0f) {
    input_angle_x += 360.0f;
  }
  // Clamp inputs to prevent out-of-bounds joint movements
  input_angle_x = constrain(input_angle_x, 0.0f, 360.0f);
  float input_angle_y = constrain(msg->y, -180.0f, 180.0f);
  float input_z_mm = constrain(msg->z, 0.0f, 1200.0f);

  // Align calibration ratios and mappings:
  // - msg->x (shoulder angle) goes to stepperX (shoulder motor, degrees_to_steps_x)
  // - msg->y (elbow angle) goes to stepperY (elbow motor, degrees_to_steps_y, inverted away from limit switch)
  // - msg->z (height in mm) goes to stepperZ (height motor, mm_to_steps_z, inverted to negative steps)
  long step_target_x = degrees_to_steps_x(input_angle_x);
  long step_target_y = degrees_to_steps_y(-input_angle_y);
  long step_target_z = mm_to_steps_z(-input_z_mm);

  target_x = input_angle_x;
  target_y = input_angle_y;
  target_z = input_z_mm;

  // Pause timer while changing parameters
  portENTER_CRITICAL(&stepperMux);
  velocity_mode = false;

  // Calculate proportional velocities to synchronize arrival times (unless streaming at high frequency)
  float run_speed_x = max_speed_x;
  float run_accel_x = accel_x;
  float run_speed_y = max_speed_y;
  float run_accel_y = accel_y;
  float run_speed_z = max_speed_z;
  float run_accel_z = accel_z;

  static unsigned long last_target_pos_time = 0;
  unsigned long now = millis();
  unsigned long dt_ms = (last_target_pos_time > 0) ? (now - last_target_pos_time) : 0;
  last_target_pos_time = now;
  streaming_mode = (dt_ms > 0 && dt_ms < 250);

  if (streaming_mode) {
    float dt_sec = (float)dt_ms / 1000.0f;
    if (dt_sec < 0.02f) dt_sec = 0.02f;

    float dist_x = abs(step_target_x - stepperX.currentPosition());
    float dist_y = abs(step_target_y - stepperY.currentPosition());
    float dist_z = abs(step_target_z - stepperZ.currentPosition());

    // Scale speed to arrive exactly in dt_sec, with a 15% margin to prevent lagging behind
    run_speed_x = (dist_x / dt_sec) * 1.15f;
    run_speed_y = (dist_y / dt_sec) * 1.15f;
    run_speed_z = (dist_z / dt_sec) * 1.15f;
  } else {
    float dist_x = abs(step_target_x - stepperX.currentPosition());
    float dist_y = abs(step_target_y - stepperY.currentPosition());
    float dist_z = abs(step_target_z - stepperZ.currentPosition());

    float time_x = (max_speed_x > 0.0f) ? (dist_x / max_speed_x) : 0.0f;
    float time_y = (max_speed_y > 0.0f) ? (dist_y / max_speed_y) : 0.0f;
    float time_z = (max_speed_z > 0.0f) ? (dist_z / max_speed_z) : 0.0f;

    float max_time = time_x;
    if (time_y > max_time) max_time = time_y;
    if (time_z > max_time) max_time = time_z;

    if (max_time > 0.001f) {
      run_speed_x = dist_x / max_time;
      run_speed_y = dist_y / max_time;
      run_speed_z = dist_z / max_time;

      float factor_x = (max_speed_x > 0.0f) ? (run_speed_x / max_speed_x) : 1.0f;
      float factor_y = (max_speed_y > 0.0f) ? (run_speed_y / max_speed_y) : 1.0f;
      float factor_z = (max_speed_z > 0.0f) ? (run_speed_z / max_speed_z) : 1.0f;

      run_accel_x = accel_x * factor_x;
      run_accel_y = accel_y * factor_y;
      run_accel_z = accel_z * factor_z;
    }
  }

  // Enforce minimum values to prevent stalls and clamp to max config values
  run_speed_x = constrain(run_speed_x, 10.0f, max_speed_x);
  run_speed_y = constrain(run_speed_y, 10.0f, max_speed_y);
  run_speed_z = constrain(run_speed_z, 10.0f, max_speed_z);
  if (run_accel_x < 10.0f) run_accel_x = 10.0f;
  if (run_accel_y < 10.0f) run_accel_y = 10.0f;
  if (run_accel_z < 10.0f) run_accel_z = 10.0f;

  if (streaming_mode) {
    stepperX.moveTo(step_target_x);
    stepperX.setSpeed(run_speed_x);

    stepperY.moveTo(step_target_y);
    stepperY.setSpeed(run_speed_y);

    stepperZ.moveTo(step_target_z);
    stepperZ.setSpeed(run_speed_z);
  } else {
    stepperX.setMaxSpeed(run_speed_x);
    stepperX.setAcceleration(run_accel_x);
    stepperX.moveTo(step_target_x);

    stepperY.setMaxSpeed(run_speed_y);
    stepperY.setAcceleration(run_accel_y);
    stepperY.moveTo(step_target_y);

    stepperZ.setMaxSpeed(run_speed_z);
    stepperZ.setAcceleration(run_accel_z);
    stepperZ.moveTo(step_target_z);
  }

  portEXIT_CRITICAL(&stepperMux);
  stepping_enabled = true;
}

// Velocity command (jog / keyboard control)
void callback_cmd_vel(const void *msgin) {
  if (current_status == "HOMING")
    return;
  const geometry_msgs__msg__Point *msg =
      (const geometry_msgs__msg__Point *)msgin;

  float vx = msg->x * STEPS_PER_DEGREE_X;
  float vy = -msg->y * STEPS_PER_DEGREE_Y;
  float vz = -msg->z * STEPS_PER_MM_Z;

  last_command = "CMD_VEL";

  portENTER_CRITICAL(&stepperMux);
  vx = constrain(vx, -max_speed_x, max_speed_x);
  vy = constrain(vy, -max_speed_y, max_speed_y);
  vz = constrain(vz, -max_speed_z, max_speed_z);

  if (fabs(vx) > 0.1f || fabs(vy) > 0.1f || fabs(vz) > 0.1f || velocity_mode) {
    if (!velocity_mode) {
      clear_velocity_queue();
      velocity_mode = true;
      stepping_enabled = true;
    }
    enqueue_velocity(vx, vy, vz);
  }
  portEXIT_CRITICAL(&stepperMux);
}

// String command callback
void callback_command(const void *msgin) {
  const std_msgs__msg__String *msg = (const std_msgs__msg__String *)msgin;
  String cmd = String(msg->data.data);
  cmd.trim();

  if (cmd == "HOMING") {
    if (current_status != "HOMING") {
      homing_requested = true;
    }
  } else if (cmd == "EMERGENCY_STOP") {
    emergency_hit = true;
    homing_requested = false;
    pause_stepping_timer();
    portENTER_CRITICAL(&stepperMux);
    velocity_mode = false;
    clear_velocity_queue();
    target_vel_x = 0.0f;
    target_vel_y = 0.0f;
    target_vel_z = 0.0f;
    current_vel_x = 0.0f;
    current_vel_y = 0.0f;
    current_vel_z = 0.0f;
    current_accel_x = 0.0f;
    current_accel_y = 0.0f;
    current_accel_z = 0.0f;
    stepperX.stop();
    stepperY.stop();
    stepperZ.stop();
    stepperX.setSpeed(0);
    stepperY.setSpeed(0);
    stepperZ.setSpeed(0);
    portEXIT_CRITICAL(&stepperMux);
    current_status = "IDLE";
    last_command = cmd;
  } else if (cmd == "RESET") {
    emergency_hit = false;
    homing_requested = false;
    stepping_enabled = false;
    velocity_mode = false;
    portENTER_CRITICAL(&stepperMux);
    clear_velocity_queue();
    target_vel_x = 0.0f;
    target_vel_y = 0.0f;
    target_vel_z = 0.0f;
    current_vel_x = 0.0f;
    current_vel_y = 0.0f;
    current_vel_z = 0.0f;
    current_accel_x = 0.0f;
    current_accel_y = 0.0f;
    current_accel_z = 0.0f;
    stepperX.stop();
    stepperY.stop();
    stepperZ.stop();
    stepperX.setSpeed(0);
    stepperY.setSpeed(0);
    stepperZ.setSpeed(0);
    portEXIT_CRITICAL(&stepperMux);
    current_status = "IDLE";
    last_command = cmd;
    resume_stepping_timer();
  } else if (cmd == "ACTION") {
    current_status = "ACTION";
    last_command = cmd;
  } else if (cmd == "IDLE") {
    current_status = "IDLE";
    last_command = cmd;
  }
}

// Servo control callback
void callback_servo_control(const void *msgin) {
  const std_msgs__msg__Float32MultiArray *msg =
      (const std_msgs__msg__Float32MultiArray *)msgin;
  if (msg->data.size < 2)
    return;
  
  float val1 = msg->data.data[0];
  float val2 = msg->data.data[1];

  // Direct float domain mapping to microsecond pulse width to prevent discretization errors
  float us1 = 500.0f + ((val1 - (-90.0f)) / 180.0f) * 1900.0f;
  float us2 = 500.0f + (val2 / 100.0f) * 1900.0f;

  servo1.writeMicroseconds(constrain((int)us1, 500, 2400));
  servo2.writeMicroseconds(constrain((int)us2, 500, 2400));
}

// Motor speed/accel config callback
void callback_config(const void *msgin) {
  const std_msgs__msg__Float32MultiArray *msg =
      (const std_msgs__msg__Float32MultiArray *)msgin;
  if (msg->data.size < 6)
    return;

  portENTER_CRITICAL(&stepperMux);
  max_speed_x = msg->data.data[0];
  accel_x     = msg->data.data[1];
  // Align Y/Z config indices directly with corrected stepper calibrations:
  max_speed_y = msg->data.data[2];
  max_speed_y = constrain(max_speed_y, 10.0f, 35000.0f);
  accel_y     = msg->data.data[3];
  accel_y     = constrain(accel_y, 10.0f, 25000.0f);
  max_speed_z = msg->data.data[4];
  max_speed_z = constrain(max_speed_z, 10.0f, 35000.0f);
  accel_z     = msg->data.data[5];
  accel_z     = constrain(accel_z, 10.0f, 25000.0f);

  stepperX.setMaxSpeed(max_speed_x);
  stepperX.setAcceleration(accel_x);
  stepperY.setMaxSpeed(max_speed_y);
  stepperY.setAcceleration(accel_y);
  stepperZ.setMaxSpeed(max_speed_z);
  stepperZ.setAcceleration(accel_z);
  portEXIT_CRITICAL(&stepperMux);

  float max_limit = max_speed_x;
  if (max_speed_y > max_limit) max_limit = max_speed_y;
  if (max_speed_z > max_limit) max_limit = max_speed_z;

  float isr_frequency = max_limit * 3.0f;
  if (isr_frequency < 10000.0f) isr_frequency = 10000.0f;
  if (isr_frequency > 80000.0f) isr_frequency = 80000.0f;

  step_interval_us = 1000000 / (uint64_t)isr_frequency;

  if (stepping_enabled && stepTimer) {
    esp_timer_stop(stepTimer);
    esp_timer_start_periodic(stepTimer, step_interval_us);
  }
}

void init_ros_comms() {
  delay(2000); // Wait for micro-ROS agent

  allocator = rcl_get_default_allocator();
  RCCHECK(rclc_support_init(&support, 0, NULL, &allocator));
  RCCHECK(rclc_node_init_default(&node, "scara_esp32_node", "", &support));

  // --- Publishers ---
  RCCHECK(rclc_publisher_init_default(
      &pub_feedback, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      "/scara/robot_feedback"));
  msg_pub_feedback.data.data = buf_pub_feedback;
  msg_pub_feedback.data.capacity = 192;
  msg_pub_feedback.data.size = 0;

  RCCHECK(rclc_publisher_init_default(
      &pub_curr_pos, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Point),
      "/scara/current_position"));

  RCCHECK(rclc_publisher_init_default(
      &pub_homing_status, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      "/scara/homing_status"));
  msg_pub_homing.data.data = buf_pub_homing;
  msg_pub_homing.data.capacity = 30;
  msg_pub_homing.data.size = 0;

  // --- Subscriptions ---
  RCCHECK(rclc_subscription_init_default(
      &sub_target_pos, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Point),
      "/scara/target_position"));

  RCCHECK(rclc_subscription_init_default(
      &sub_cmd_vel, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Point),
      "/scara/cmd_vel"));

  RCCHECK(rclc_subscription_init_default(
      &sub_command, &node, ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
      "/scara/command"));
  msg_sub_command.data.data = buf_sub_command;
  msg_sub_command.data.capacity = 64;
  msg_sub_command.data.size = 0;

  RCCHECK(rclc_subscription_init_default(
      &sub_servo_control, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
      "/scara/servo_control"));
  msg_sub_servo.data.data = buf_sub_servo_data;
  msg_sub_servo.data.capacity = 2;
  msg_sub_servo.data.size = 0;

  RCCHECK(rclc_subscription_init_default(
      &sub_config, &node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray),
      "/scara/config"));
  msg_sub_config.data.data = config_buffer;
  msg_sub_config.data.capacity = 6;
  msg_sub_config.data.size = 0;

  // --- Executor ---
  RCCHECK(rclc_executor_init(&executor, &support.context, 5, &allocator));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &sub_target_pos, &msg_sub_target, &callback_target_position,
      ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &sub_cmd_vel, &msg_sub_vel, &callback_cmd_vel, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_command,
                                         &msg_sub_command, &callback_command,
                                         ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(&executor, &sub_servo_control,
                                         &msg_sub_servo,
                                         &callback_servo_control, ON_NEW_DATA));
  RCCHECK(rclc_executor_add_subscription(
      &executor, &sub_config, &msg_sub_config, &callback_config, ON_NEW_DATA));
}

void spin_ros_comms() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(0));

  // Publish position and status feedback
  static unsigned long last_fb = 0;
  if (millis() - last_fb >= 60) {
    last_fb = millis();
    publish_ros_feedback();

    portENTER_CRITICAL(&stepperMux);
    long loop_cur_x = stepperX.currentPosition();
    long loop_cur_y = stepperY.currentPosition();
    long loop_cur_z = stepperZ.currentPosition();
    portEXIT_CRITICAL(&stepperMux);

    // Align feedback mapping and calibration:
    // - msg_pub_curr_pos.x (shoulder angle) comes from loop_cur_x (STEPS_PER_DEGREE_X)
    // - msg_pub_curr_pos.y (elbow angle) comes from loop_cur_y (elbow motor, STEPS_PER_DEGREE_Y, inverted)
    // - msg_pub_curr_pos.z (height in mm) comes from loop_cur_z (height motor, STEPS_PER_MM_Z, inverted)
    msg_pub_curr_pos.x = (float)loop_cur_x / STEPS_PER_DEGREE_X;
    msg_pub_curr_pos.y = -(float)loop_cur_y / STEPS_PER_DEGREE_Y;
    msg_pub_curr_pos.z = -(float)loop_cur_z / STEPS_PER_MM_Z;
    RCSOFTCHECK(rcl_publish(&pub_curr_pos, &msg_pub_curr_pos, NULL));
  }
}

void spin_ros_some() {
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(0));
}

void publish_ros_feedback() {
  if (current_status == "HOMING") {
    publish_string_msg(&pub_homing_status, &msg_pub_homing, "RUNNING");
  } else if (last_command == "HOMING" && current_status == "IDLE") {
    publish_string_msg(&pub_homing_status, &msg_pub_homing, "SUCCESS");
  } else if (emergency_hit) {
    publish_string_msg(&pub_homing_status, &msg_pub_homing, "FAILED");
  }

  if (current_status != "HOMING" && current_status != "ACTION" && current_status != "EMERGENCY_STOP") {
    current_status =
        (stepperX.isRunning() || stepperY.isRunning() || stepperZ.isRunning())
            ? "MOVING"
            : "IDLE";
  }

  portENTER_CRITICAL(&stepperMux);
  long cur_x = stepperX.currentPosition();
  long cur_y = stepperY.currentPosition();
  long cur_z = stepperZ.currentPosition();
  portEXIT_CRITICAL(&stepperMux);

  // Align feedback mapping and calibration:
  // - cy (elbow angle) comes from cur_y (elbow motor, STEPS_PER_DEGREE_Y, inverted)
  // - cz (height in mm) comes from cur_z (height motor, STEPS_PER_MM_Z, inverted)
  float cx = (float)cur_x / STEPS_PER_DEGREE_X;
  float cy = -(float)cur_y / STEPS_PER_DEGREE_Y;
  float cz = -(float)cur_z / STEPS_PER_MM_Z;

  snprintf(buf_pub_feedback, msg_pub_feedback.data.capacity,
           "cx:%.2f|cy:%.2f|cz:%.2f|tx:%.2f|ty:%.2f|tz:%.2f|st:%s|cmd:%s|en:%d",
           cx, cy, cz, target_x, target_y, target_z, current_status.c_str(),
           last_command.c_str(), motor_enabled);
  msg_pub_feedback.data.size = strlen(buf_pub_feedback);
  RCSOFTCHECK(rcl_publish(&pub_feedback, &msg_pub_feedback, NULL));
}
