#!/usr/bin/env python3
"""
SCARA Robot — Bridge Node
Acts as a parameter bridge: exposes speed/accel as ROS2 parameters and
publishes them to /scara/config so the ESP32 firmware can read them live.
Also accepts dynamic updates via /scara/config_update from the GUI.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray


class ScaraBridgeNode(Node):
    def __init__(self):
        super().__init__('scara_bridge_node')

        # Declare ROS2 parameters with defaults (speed and accel per axis)
        self.declare_parameter('max_speed_x', 8000.0)
        self.declare_parameter('max_accel_x', 5000.0)
        self.declare_parameter('max_speed_y', 12000.0)
        self.declare_parameter('max_accel_y', 5000.0)
        self.declare_parameter('max_speed_z', 8000.0)
        self.declare_parameter('max_accel_z', 5000.0)

        # Publisher: sends config to ESP32 firmware
        self.config_pub = self.create_publisher(Float32MultiArray, '/scara/config', 10)

        # Subscriber: accepts live config updates from the GUI sliders
        self.config_update_sub = self.create_subscription(
            Float32MultiArray, '/scara/config_update', self._config_update_cb, 10)

        # Heartbeat timer: re-send current config every 0.5 s
        self.timer = self.create_timer(0.5, self._publish_current_config)

        self.get_logger().info('Scara Bridge Node started — independent config heartbeat active.')

    def _config_update_cb(self, msg):
        """Receive [speed_x, accel_x, speed_y, accel_y, speed_z, accel_z] from GUI and update params."""
        if len(msg.data) < 6:
            return
        self.set_parameters([
            rclpy.parameter.Parameter('max_speed_x', value=float(msg.data[0])),
            rclpy.parameter.Parameter('max_accel_x', value=float(msg.data[1])),
            rclpy.parameter.Parameter('max_speed_y', value=float(msg.data[2])),
            rclpy.parameter.Parameter('max_accel_y', value=float(msg.data[3])),
            rclpy.parameter.Parameter('max_speed_z', value=float(msg.data[4])),
            rclpy.parameter.Parameter('max_accel_z', value=float(msg.data[5])),
        ])
        self.get_logger().info(
            f'Config updated — '
            f'X(spd:{msg.data[0]:.0f}, acc:{msg.data[1]:.0f}) '
            f'Y(spd:{msg.data[2]:.0f}, acc:{msg.data[3]:.0f}) '
            f'Z(spd:{msg.data[4]:.0f}, acc:{msg.data[5]:.0f})')
        self._publish_current_config()

    def _publish_current_config(self):
        sx  = float(self.get_parameter('max_speed_x').value)
        ax  = float(self.get_parameter('max_accel_x').value)
        sy  = float(self.get_parameter('max_speed_y').value)
        ay  = float(self.get_parameter('max_accel_y').value)
        sz  = float(self.get_parameter('max_speed_z').value)
        az  = float(self.get_parameter('max_accel_z').value)

        msg = Float32MultiArray()
        msg.data = [sx, ax, sy, ay, sz, az]
        self.config_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ScaraBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
