#!/bin/bash
# =============================================================================
# SCARA Robot - Bridge Node Launch Script
# =============================================================================

echo "=========================================="
echo "  SCARA Robot - Bridge Node (Config)"
echo "=========================================="

# Source ROS2 Jazzy
echo "[1/3] Sourcing ROS2 Jazzy..."
source /opt/ros/jazzy/setup.bash

# Source micro-ROS agent workspace
echo "[2/3] Sourcing micro-ROS workspace..."
source /home/amir/microros_ws/install/setup.bash

# Source SCARA project
echo "[3/3] Sourcing SCARA project..."
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source install/setup.bash

echo ""
echo "=========================================="
echo "  Bridge Node Running"
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Run bridge node
ros2 run scara_cfg_bridge bridge_node
