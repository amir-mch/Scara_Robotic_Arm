#include "homing_module.h"
#include "stepper_core.h"
#include "kinematics_engine.h"
#include "ros_comms.h"

volatile bool homing_requested = false;

void initHomingSystem() {
  homing_requested = false;
}

void runHomingSequence() {
  pause_stepping_timer(); // Disable background timer interrupt to avoid concurrency races
  velocity_mode = false;
  emergency_hit = false;
  current_status = "HOMING";
  last_command = "HOMING";
  publish_ros_feedback();
  set_motor_state(1);

  bool y_homed = false;
  bool x_retracted = false;
  long x_start = stepperX.currentPosition();

  // Start Y moving fast towards limit switch
  stepperY.setSpeed(DIR_Y_HOMING * HOMING_FAST_Y);

  // Start X moving away from limit switch (Safe Posture Opening)
  stepperX.setSpeed(-DIR_X_HOMING * HOMING_FAST_X);

  // Z is idle
  stepperZ.setSpeed(0);

  unsigned long last_yield = millis();

  // ── Phase 1: Start Y Homing (parallel) & X Safe Posture Retract ──
  while (!y_homed || !x_retracted) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    // Step Y fast towards switch
    if (!y_homed) {
      if (digitalRead(LIMIT_Y_PIN) == LOW) {
        stepperY.setSpeed(0);
        y_homed = true;
      } else {
        stepperY.runSpeed();
      }
    }

    // Retract X away from switch
    if (!x_retracted) {
      if (abs(stepperX.currentPosition() - x_start) >= 1000) {
        stepperX.setSpeed(0);
        x_retracted = true;
      } else {
        stepperX.runSpeed();
      }
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1); // Feed ESP32 Watchdog
    }
  }

  // Y and Z now proceed: Z starts priority homing while Y finishes its cycle.
  // Start Z moving fast towards limit switch
  stepperZ.setSpeed(DIR_Z_HOMING * HOMING_FAST_Z);
  
  // Set Y to backoff
  bool z_fast_hit = false;
  bool y_backoff_done = false;
  long y_backoff_start = stepperY.currentPosition();
  stepperY.setSpeed(-DIR_Y_HOMING * HOMING_FAST_Y);

  while (!z_fast_hit || !y_backoff_done) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    // Step Z fast towards switch
    if (!z_fast_hit) {
      if (digitalRead(LIMIT_Z_PIN) == LOW) {
        stepperZ.setSpeed(0);
        z_fast_hit = true;
      } else {
        stepperZ.runSpeed();
      }
    }

    // Retract Y away from switch
    if (!y_backoff_done) {
      if (abs(stepperY.currentPosition() - y_backoff_start) >= HOMING_BACKOFF_Y) {
        stepperY.setSpeed(0);
        stepperY.setSpeed(DIR_Y_HOMING * HOMING_SLOW_Y);
        y_backoff_done = true;
      } else {
        stepperY.runSpeed();
      }
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1);
    }
  }

  // Z backoff and Y slow approach
  bool z_backoff_done = false;
  long z_backoff_start = stepperZ.currentPosition();
  stepperZ.setSpeed(-DIR_Z_HOMING * HOMING_FAST_Z);

  bool y_slow_hit = false;

  while (!z_backoff_done || !y_slow_hit) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    // Retract Z away from switch
    if (!z_backoff_done) {
      if (abs(stepperZ.currentPosition() - z_backoff_start) >= HOMING_BACKOFF_Z) {
        stepperZ.setSpeed(0);
        stepperZ.setSpeed(DIR_Z_HOMING * HOMING_SLOW_Z);
        z_backoff_done = true;
      } else {
        stepperZ.runSpeed();
      }
    }

    // Step Y slow towards switch
    if (!y_slow_hit) {
      if (digitalRead(LIMIT_Y_PIN) == LOW) {
        stepperY.setSpeed(0);
        stepperY.setCurrentPosition(0);
        y_slow_hit = true;
      } else {
        stepperY.runSpeed();
      }
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1);
    }
  }

  // Z slow approach to zero
  bool z_slow_hit = false;
  while (!z_slow_hit) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    // Step Z slow towards switch
    if (digitalRead(LIMIT_Z_PIN) == LOW) {
      stepperZ.setSpeed(0);
      stepperZ.setCurrentPosition(0);
      z_slow_hit = true;
    } else {
      stepperZ.runSpeed();
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1);
    }
  }

  // ── Phase 3: Z is safe and homed. Now X can do final homing ──
  // X fast towards limit switch
  stepperX.setSpeed(DIR_X_HOMING * HOMING_FAST_X);
  bool x_fast_hit = false;
  while (!x_fast_hit) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    if (digitalRead(LIMIT_X_PIN) == LOW) {
      stepperX.setSpeed(0);
      x_fast_hit = true;
    } else {
      stepperX.runSpeed();
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1);
    }
  }

  // X backoff away from switch
  long x_backoff_start = stepperX.currentPosition();
  stepperX.setSpeed(-DIR_X_HOMING * HOMING_FAST_X);
  bool x_backoff_done = false;
  while (!x_backoff_done) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    if (abs(stepperX.currentPosition() - x_backoff_start) >= HOMING_BACKOFF_X) {
      stepperX.setSpeed(0);
      stepperX.setSpeed(DIR_X_HOMING * HOMING_SLOW_X);
      x_backoff_done = true;
    } else {
      stepperX.runSpeed();
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1);
    }
  }

  // X slow approach to zero
  bool x_slow_hit = false;
  while (!x_slow_hit) {
    if (emergency_hit) {
      publish_ros_feedback();
      resume_stepping_timer();
      return;
    }

    if (digitalRead(LIMIT_X_PIN) == LOW) {
      stepperX.setSpeed(0);
      stepperX.setCurrentPosition(0);
      x_slow_hit = true;
    } else {
      stepperX.runSpeed();
    }

    if (millis() - last_yield >= 10) {
      last_yield = millis();
      spin_ros_some();
      delay(1);
    }
  }

  // Homing complete!
  target_x = 0.0f;
  target_y = 0.0f;
  target_z = 0.0f;
  current_status = "IDLE";
  publish_ros_feedback();

  resume_stepping_timer(); // Re-enable background step timer for normal operation
}
