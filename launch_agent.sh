#!/bin/bash
# =============================================================================
# SCARA Robot - Full Launch Script
# Sources all required workspaces and starts the micro-ROS agent
# =============================================================================

echo "=========================================="
echo "  SCARA Robot - Launch Script"
echo "=========================================="

# Source ROS2 Jazzy
echo "[1/4] Sourcing ROS2 Jazzy..."
source /opt/ros/jazzy/setup.bash

# Source micro-ROS agent workspace
echo "[2/4] Sourcing micro-ROS agent workspace..."
source /home/amir/microros_ws/install/setup.bash

# Build and source SCARA project
echo "[3/4] Building and sourcing SCARA project..."
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
colcon build --symlink-install > /dev/null 2>&1
source install/setup.bash

# Check if USB device exists
USB_PORT="/dev/ttyUSB0"
if [ ! -e "$USB_PORT" ]; then
    echo "[!] Warning: $USB_PORT not found!"
    echo "    Please connect your ESP32 and check the port with: ls /dev/ttyUSB*"
    echo ""
fi

echo "[4/4] Starting micro-ROS agent on $USB_PORT..."
echo ""
echo "=========================================="
echo "  micro-ROS Agent Running"
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Run micro-ROS agent
ros2 run micro_ros_agent micro_ros_agent serial --dev $USB_PORT -b 115200
