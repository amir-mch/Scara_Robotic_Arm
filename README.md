# SCARA Robot Control Center 🤖📊

A complete, high-performance control and simulation ecosystem for a 3-Axis SCARA (Selective Compliance Assembly Robot Arm) manipulator. The project integrates **ESP32 RTOS firmware** driving high-precision stepper motors, a **ROS 2 Jazzy message bridge** handling micro-ROS telemetry, and a state-of-the-art **PyQt5 Desktop Dashboard** featuring real-time 2D simulation, calibration offsets, and trajectory learning.

---

## 🌟 Key Features

*   **🎨 PyQt5 Premium Dark Dashboard**: A sleek, modern user interface utilizing a Catppuccin-inspired dark theme with rounded cards, custom controls, and styled sliders.
*   **📈 Real-Time 2D SCARA Simulator**: An interactive vector painter showing current arm joint angles and targets, featuring smooth Exponential Moving Average (EMA) position tracking and a fading coordinate path trail.
*   **🛠️ Calibration & Inverse Kinematics (IK)**: Integrated analytical 2D IK solver featuring joint angular offset calibration (`Off1_deg` & `Off2_deg`) directly in target calculations and live Cartesian Forward Kinematics telemetry.
*   **🚀 Smooth Trajectory Teach-and-Playback**: Bypasses heavy real-time acceleration profiling in high-frequency (10Hz) streaming mode by calculating velocities dynamically ($V_{\text{stream}} = \frac{\text{dist}}{dt} \times 1.15$) and executing via direct speed ticks (`runSpeedToPosition()`) in the ESP32 timer interrupt.
*   **🎮 Keyboard & Manual Jog Control**: Responsive WASD direction control (elbow/shoulder jogging) and QE control (vertical height axis) featuring hardware debouncing via native Qt auto-repeat filters.
*   **📟 Thread-Safe Log Console**: Rich text scroll console highlighting informational, success, warning, and error logs with dim grey timestamps.

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph PC["PC (Host Machine)"]
        A[PyQt5 GUI Control Center] <-->|QTimer Polling 30Hz| B[Thread-Safe State Manager]
        A -->|Keyboard Jog / IK Commands| C[Velocity Stream Worker]
        C -->|geometry_msgs/Point| D[ROS 2 Jazzy Node]
        D <-->|micro-ROS Transport| E[micro-ROS Serial Agent]
    end
    subgraph MCU["Microcontroller"]
        E <-->|USB Serial| F[ESP32 micro-ROS Subscriber/Publisher]
        F -->|State Update Commands| G[Motion Control Task]
        G -->|Direct Speed Overrides| H[Stepper Timer Interrupt ISR (Core 0)]
        H -->|PWM Step/Dir pulses| I[Shoulder / Elbow / Z-Axis Steppers]
    end
```

---

## 📂 Project Structure

*   `src/scara_cfg_bridge/` : The ROS 2 Python package holding the desktop application.
    *   `scara_cfg_bridge/gui_node.py` : Main application entry point managing Qt event loops and background threads.
    *   `scara_cfg_bridge/gui_panels_pyqt.py` : PyQt5 dashboard layout panels.
    *   `scara_cfg_bridge/gui_animations.py` : Animations module handling pulsing LED gauges and the 2D SCARA painter canvas.
    *   `scara_cfg_bridge/ros_node.py` : ROS 2 subscriber/publisher bridge.
    *   `scara_cfg_bridge/kinematics.py` : Analytical Inverse and Forward Kinematics solvers.
*   `src/firmware/firmware/` : ESP32 C++ microcontroller firmware.
    *   `firmware.ino` : Core setup, micro-ROS configurations, and main loop.
    *   `ros_comms.cpp` : Micro-ROS callback handlers for target position streaming and velocity jogging.
    *   `stepper_core.cpp` : High-frequency timer interrupts, step calculations, and motor configurations.
    *   `homing_module.cpp` : Virtual kinematic homing sequences for limit switches.

---

## 🛠️ Installation & Build

### Prerequisites
*   **Ubuntu Linux** (configured with ROS 2 Jazzy)
*   **micro-ROS Workspace** (compiled for serial transport)
*   **Python 3** with `PyQt5` installed

### Step 1: Install PyQt5 dependencies
```bash
pip install PyQt5
```

### Step 2: Build the ROS 2 Workspace
Open a terminal in the root of the workspace directory and run:
```bash
colcon build --packages-select scara_cfg_bridge
```

---

## 🚀 How to Run the Ecosystem

The workspace includes convenient shell scripts to launch each module:

### 1. Launch the micro-ROS Serial Agent
Connect your programmed ESP32 to the PC and run:
```bash
./launch_agent.sh
```

### 2. Launch the Parameter & Command Bridge
In a new terminal window:
```bash
./launch_bridge.sh
```

### 3. Launch the GUI Dashboard
In a new terminal window:
```bash
./launch_gui.sh
```

---

## 🎮 Interface Guide

*   **Keyboard Jog:** Hold `W`/`S` to jog Joint 2, `A`/`D` to jog Joint 1, and `Q`/`E` to raise/lower the height (Joint 3). Press `Space` or `Esc` to trigger an Emergency Stop.
*   **Calibration Offsets:** Home the robot, align the physical links manually, note the offset angles from target $0^\circ$, and enter them in `Off1` and `Off2` in the **Cartesian (IK)** tab to calibrate coordinates.
*   **Trajectory Learning:** Click `Start Learn`, manually jog the robot along a desired path, click `Stop Learn`, and click `Start Loop` to repeat the trajectory in a continuous, smooth back-and-forth loop.
