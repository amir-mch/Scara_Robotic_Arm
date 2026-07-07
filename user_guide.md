# SCARA Robot User & Control Dashboard Guide

Welcome to the SCARA Robot Control Dashboard! This guide is designed for absolute beginners to help you understand the control interface, how to launch the software, and how to operate the robot safely.

---

## 1. Quick Start: How to Launch the Robot

To launch the dashboard, open three separate terminal windows and run the following commands sequentially:

1. **Terminal 1: Start the micro-ROS Serial Agent**
   This establishes serial communication with the ESP32 microcontroller:
   ```bash
   cd ~/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace
   ./launch_agent.sh
   ```
2. **Terminal 2: Start the Parameter Bridge Node**
   This node manages speed and acceleration parameters:
   ```bash
   cd ~/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace
   ./launch_bridge.sh
   ```
3. **Terminal 3: Start the GUI Dashboard**
   This launches the user interface:
   ```bash
   cd ~/Desktop/Project/Scara-v2.1.0.0/SCARA_WorkSpace
   ./launch_gui.sh
   ```

---

## 2. Dashboard Interface: Section-by-Section

### A. Connection Panel (Top Left)
- **What it does:** Displays the live status of the communication bridge between the GUI and the physical ESP32 robot core.
- **How to verify link:**
  - **● Connected** (Green): The ESP32 is actively transmitting position feedback, and the system is ready.
  - **● Waiting for data...** (Red/Yellow): The GUI is running, but no data packets are being received from the microcontroller. Verify the ESP32 is plugged in and the agent is running in Terminal 1.
  - **● Connection Lost!** (Red): The connection was active but has dropped (no feedback packets for >2.0 seconds). Check USB cabling.

---

### B. Jog Control Panel (Top Right)
- **What it does:** Allows you to manually move (jog) individual motors using keyboard shortcuts or on-screen buttons.
- **Manual Keys (WASDQE):**
  - **W / S**: Jog Joint 1 forward/backward (X-axis equivalent).
  - **A / D**: Jog Joint 2 forward/backward (Y-axis equivalent).
  - **Q / E**: Jog Z-axis up/down.
- **Global Speed Slider:**
  - Sets the velocity override value for jogging movements. Dragging it to the right increases manual movement speed, while dragging it to the left makes movements slower and more precise.
- **Safety Note:** Pressing any manual key starts movement; releasing the key immediately ramps the speed down to zero. 
- *Note: Keyboard jogging is disabled when you are actively typing coordinates in text fields to prevent accidental movements.*

---

### C. Joint Space Target Panel (Center Left)
- **What it does:** Direct control of target angles in joint space.
- **How to operate safely:**
  - Type the desired angles for Joint 1 (X in degrees), Joint 2 (Y in degrees), and vertical linear height (Z in millimeters).
  - Click **Send Target** to initiate smooth, coordinated S-curve acceleration movement towards those specific coordinates.
  - **Status check:** Verify the status changes to **MOVING** during transit and returns to **IDLE** once reached.

---

### D. Cartesian IK (Inverse Kinematics) Panel (Center Right)
- **What it does:** Translates $X, Y, Z$ millimetric coordinates into physical joint angles using trigonometry.
- **How Inverse Kinematics works:**
  Instead of telling the joints to rotate, you specify where the end of the robot arm (end-effector) should be in physical space ($X, Y, Z$ in millimeters relative to the base center).
- **Link Lengths ($L_1$, $L_2$):**
  - **L1 (mm)**: Length of the first segment of the arm (shoulder to elbow).
  - **L2 (mm)**: Length of the second segment of the arm (elbow to hand).
  - *Verify these lengths match your physical robot setup before sending commands.*
- **How to send coordinates safely:**
  - Type the desired Cartesian position ($X$ and $Y$ coordinates in millimeters, and height $Z$ in millimeters).
  - Choose the desired geometric layout (**Elbow UP** or **Elbow DOWN**).
  - Click **Apply Cartesian Target** to run the Inverse Kinematics math and automatically command the joint steppers.

---

### E. Motor Speed / Accel Panel (Lower Center)
- **What it does:** Configures the maximum speed and acceleration of **each axis independently**.
- **Adjusting Speed & Accel:**
  - Use the sliders to independently set the maximum steps/sec (`Speed`) and steps/sec² (`Accel`) for **Joint X**, **Joint Y**, and **Axis Z**.
  - Click **Apply Motor Config** to transmit the configurations to the parameter server and immediately update the ESP32's motion profiles.
  - *Dynamic Interupt Tuning:* The ESP32 firmware automatically scales its core stepping calculation interrupts to match your configuration.

---

### F. Servo & Homing Panel (Lower Left)
- **Homing Sequence:**
  - Before running Cartesian or Joint targets, the robot must calibrate its position.
  - Click **🏠 Homing Sequence** to drive all axes into their respective limit switches.
  - Once limit switches trigger, the joints set their home coordinates to `0` and transition to **IDLE**.
- **Auxiliary Servo Control:**
  - **Servo 1**: Adjusts gripper/wrist angle slider from $-90^\circ$ to $90^\circ$.
  - **Servo 2**: Adjusts gripper open/close grip intensity slider from $0\%$ to $100\%$.
  - Click **Set Servos** to apply the positions.
- **Emergency Stop:**
  - Pressing the **Spacebar** or clicking **⛔ EMERGENCY STOP** halts all motor pulses and cuts power to the stepping coils.
  - Click **🔄 Reset** to recover and resume operation.
