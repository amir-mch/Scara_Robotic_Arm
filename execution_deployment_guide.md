# SCARA Robot Execution & Deployment Guide

This guide provides instructions to compile and flash the updated ESP32 firmware, source and run the ROS 2 workspace, and execute a safe testing protocol on the hardware.

---

## 1. Firmware Compilation & Flashing

Ensure you have the ESP32 board index installed in `arduino-cli`. If not, configure it first.

### A. Pre-requisites & Library Installation
Install the necessary Arduino libraries using `arduino-cli`:
```bash
# Add ESP32 board URL if needed
arduino-cli config init
arduino-cli core update-index
arduino-cli core install esp32:esp32

# Install required external libraries
arduino-cli lib install "AccelStepper"
arduino-cli lib install "ESP32Servo"
# Note: For micro_ros_arduino, install the library .zip from the official release or via:
# arduino-cli lib install "micro_ros_arduino"
```

### B. Compile the Firmware
Run the following compilation command:
```bash
arduino-cli compile --fqbn esp32:esp32:esp32 /home/amir/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace/src/firmware/firmware
```
*Note: If you are using a specific dev module, adjust the FQBN accordingly (e.g. `esp32:esp32:esp32da` or `esp32:esp32:devkitv1`).*

### C. Flash the Firmware
Upload the compiled binary to your ESP32 board via the serial port (typically `/dev/ttyUSB0` on Ubuntu):
```bash
# Verify USB connection permissions
sudo chmod a+rw /dev/ttyUSB0

# Upload the binary
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 /home/amir/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace/src/firmware/firmware
```

---

## 2. ROS 2 Workspace Sourcing & Launching

Open three separate terminals to run each component.

### Terminal 1: Launch micro-ROS Agent
The agent acts as the serial-to-ROS2 middleware.
```bash
# Source ROS2 Jazzy and micro-ROS agent workspace
source /opt/ros/jazzy/setup.bash
source /home/amir/microros_ws/install/setup.bash

# Run micro-ROS agent
ros2 run micro_ros_agent micro_ros_agent serial --dev /dev/ttyUSB0 -b 115200
```

### Terminal 2: Build & Launch Parameter Bridge
The bridge node exposes speed/accel as ROS2 parameters.
```bash
# Source ROS2 Jazzy and micro-ROS agents
source /opt/ros/jazzy/setup.bash
source /home/amir/microros_ws/install/setup.bash

# Build and source SCARA project workspace
cd /home/amir/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace
colcon build --packages-select scara_cfg_bridge
source install/setup.bash

# Run bridge node
ros2 run scara_cfg_bridge bridge_node
```

### Terminal 3: Launch GUI Dashboard
The Tkinter GUI provides direct Joint/Cartesian controls and visual feedback.
```bash
# Source ROS2 Jazzy and SCARA project workspace
source /opt/ros/jazzy/setup.bash
source /home/amir/microros_ws/install/setup.bash
cd /home/amir/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace
source install/setup.bash

# Run GUI node
ros2 run scara_cfg_bridge gui_node
```

---

## 3. Step-by-Step Launch & Safety Test Protocol

> [!CAUTION]
> **Safety First**: Do not switch on the high-voltage motor power supply during the initial logic verification steps (Steps 1 & 2).

### Step 1: Logic-Only Connection Verification
1. Connect the ESP32 to the host computer using a USB cable. **Keep the motor power supply turned OFF**.
2. Start the micro-ROS Agent, Bridge, and GUI nodes.
3. Check the top-right status label on the GUI: it should transition from **● Waiting for data...** to **● Connected**.
4. Verify the GUI log output: it should display current joint coordinates (e.g. `X=0.00`, `Y=0.00`, `Z=0.00`).

### Step 2: Emergency Stop & Limit Switch Verification
1. Press the **SPACEBAR** or click the red **EMERGENCY STOP** button on the GUI.
2. Confirm the log prints: `[HH:MM:SS] EMERGENCY STOP triggered!`.
3. Manually depress the physical limit switches (limit switches X, Y, Z) one-by-one.
4. Verify on the GUI dashboard that the corresponding motor status indicator flags or positions register appropriately.
5. Click **Reset** in the GUI to clear the emergency state before proceeding.

### Step 3: Homing Safety Loop Interrupt Test
1. Turn ON the motor power supply.
2. Click **🏠 Homing Sequence** on the GUI. The joints will start moving toward the limit switches.
3. Immediately press the **SPACEBAR** (Emergency Stop).
4. **Verification**: Confirm that all three motors stop moving **instantly**. The GUI log must report `Homing: FAILED` and the motors must disengage.
5. Click **Reset** on the GUI, and click **🏠 Homing Sequence** again. Allow the robot to complete homing. It should register `Homing: SUCCESS` once all limits are reached.

### Step 4: Joint Space & Cartesian Space Control Verification
1. In the **Joint Space** tab, enter small target angles (e.g. `X: 10`, `Y: 10`, `Z: 5`) and click **Send Target Position**. The robot must execute a smooth, S-curve linear ramp profile to the target.
2. Switch to the **Cartesian (IK)** tab:
   - Enter default link lengths: `L1: 200`, `L2: 150`.
   - Enter Cartesian coordinates (e.g. `X: 180`, `Y: 100`, `Z: 10`).
   - Click **Send Cartesian Target**. Verify the GUI translates this smoothly into joint angles ($\theta_1, \theta_2$) and the robot moves smoothly to the calculated coordinates.
3. Switch back to Cartesian and input an out-of-reach target (e.g. `X: 400`, `Y: 400`).
   - **Verification**: The GUI must display an `IK Limit Error` alert box and block command transmission to the firmware.

---

## 4. Diagnostics & Log Verification

To confirm that the 30ms streaming thread and the firmware playout queue are communicating correctly, inspect the following:

* **GUI Terminal**: Watch for runtime warnings. If the ROS2 publisher queue gets blocked, Python will print queue warnings. S-curve calculation print logs inside Tkinter console will read:
  `Cartesian Target: X=... Y=... Z=... -> Joint1=... Joint2=...`
* **micro-ROS Agent Terminal**: Ensure the serial packet traffic is steady. Look for any transmission loss reports or frame errors. A healthy connection will continuously report serial reads and writes without buffer overrun alerts.
* **Firmware Diagnostics**: If the playout buffer experiences starvation or overrun:
  - If packages drop and are delayed by $>150\text{ms}$, the firmware timeout will trigger a smooth deceleration to $0$. Watch for micro-stuttering. If the motion is unbroken, playout interpolation is working.
  - The board activity LED (on pin 4) will blink at a steady 1Hz rate, indicating the main loop continues spinning without blocking delays.
