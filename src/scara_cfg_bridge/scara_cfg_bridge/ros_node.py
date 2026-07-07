import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import String, Float32MultiArray

class ScaraRosNode(Node):
    def __init__(self, state_manager):
        super().__init__('scara_gui_node')
        self.state_manager = state_manager

        # Publishers
        self.pos_pub    = self.create_publisher(Point,              '/scara/target_position', 10)
        self.vel_pub    = self.create_publisher(Point,              '/scara/cmd_vel',         10)
        self.cmd_pub    = self.create_publisher(String,             '/scara/command',         10)
        self.servo_pub   = self.create_publisher(Float32MultiArray,  '/scara/servo_control',   10)
        self.config_pub  = self.create_publisher(Float32MultiArray,  '/scara/config_update',   10)
        self.config_direct_pub = self.create_publisher(Float32MultiArray, '/scara/config',     10)

        # Subscribers
        self.create_subscription(String, '/scara/robot_feedback',  self._feedback_cb, 10)
        self.create_subscription(Point,  '/scara/current_position', self._pos_cb,      10)
        self.create_subscription(String, '/scara/homing_status',   self._homing_cb,   10)

    def _feedback_cb(self, msg):
        try:
            parts = dict(kv.split(':', 1) for kv in msg.data.split('|'))
            current_pos = {
                'x': float(parts.get('cx', 0)),
                'y': float(parts.get('cy', 0)),
                'z': float(parts.get('cz', 0)),
            }
            target_pos = {
                'x': float(parts.get('tx', 0)),
                'y': float(parts.get('ty', 0)),
                'z': float(parts.get('tz', 0)),
            }
            status = parts.get('st',  'IDLE')
            last_cmd = parts.get('cmd', 'NONE')
            motor_en = int(parts.get('en', 1))
            self.state_manager.update_feedback(current_pos, target_pos, status, last_cmd, motor_en)
        except Exception:
            pass

    def _pos_cb(self, msg):
        with self.state_manager._lock:
            self.state_manager.current_pos = {'x': msg.x, 'y': msg.y, 'z': msg.z}
            self.state_manager.feedback_received = True

    def _homing_cb(self, msg):
        with self.state_manager._lock:
            self.state_manager.homing_status = msg.data

    def send_target(self, x, y, z):
        msg = Point()
        msg.x, msg.y, msg.z = float(x), float(y), float(z)
        self.pos_pub.publish(msg)

    def send_velocity(self, vx, vy, vz):
        msg = Point()
        msg.x, msg.y, msg.z = float(vx), float(vy), float(vz)
        self.vel_pub.publish(msg)

    def send_command(self, cmd):
        msg = String()
        msg.data = cmd
        self.cmd_pub.publish(msg)

    def send_servos(self, a1, a2):
        msg = Float32MultiArray()
        msg.data = [float(a1), float(a2)]
        self.servo_pub.publish(msg)

    def send_config(self, sx, ax, sy, ay, sz, az):
        msg = Float32MultiArray()
        msg.data = [float(sx), float(ax), float(sy), float(ay), float(sz), float(az)]
        self.config_direct_pub.publish(msg)
        self.config_pub.publish(msg)

    def stop_all(self):
        """Emergency: stop steppers via command and zero velocity."""
        cmd = String()
        cmd.data = 'EMERGENCY_STOP'
        self.cmd_pub.publish(cmd)
        self.send_velocity(0.0, 0.0, 0.0)
