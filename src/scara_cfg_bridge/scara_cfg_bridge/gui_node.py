#!/usr/bin/env python3
import sys
import time
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QSlider, QRadioButton, 
    QButtonGroup, QPushButton, QGroupBox, QTextEdit, QFrame,
    QTabWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat

import rclpy

# Local imports
from scara_cfg_bridge.state_manager import ScaraState
from scara_cfg_bridge.kinematics import calculate_inverse_kinematics, calculate_forward_kinematics
from scara_cfg_bridge.velocity_worker import VelocityStreamingWorker
from scara_cfg_bridge.ros_node import ScaraRosNode

# PyQt5 UI panels and animations
from scara_cfg_bridge.gui_panels_pyqt import (
    PositionPanel, JogPanel, JointSpacePanel, CartesianIKPanel,
    ServoPanel, MotorConfigPanel, ActionPanel, LogPanel, AutomationLoopPanel
)
from scara_cfg_bridge.gui_animations import StatusPulsator, ScaraVisualizerWidget

class ScaraApp(QMainWindow):
    # Log signal to route log messages thread-safely from background workers to QHTML log console
    log_signal = pyqtSignal(str, str)

    # Key mappings for keyboard jogging
    _JOG_KEY_MAP = {
        Qt.Key_W: (0,  1,  0),
        Qt.Key_S: (0, -1,  0),
        Qt.Key_A: (-1, 0,  0),
        Qt.Key_D: ( 1, 0,  0),
        Qt.Key_Q: (0,  0,  1),
        Qt.Key_E: ( 0, 0, -1),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCARA Robot Control Center")
        self.resize(1150, 750)

        # Theme Color definitions
        self.BG = '#1e1e2e'
        self.BG_LIGHT = '#252538'
        self.BG_CARD = '#2a2a40'
        self.FG = '#cdd6f4'
        self.FG_DIM = '#7f849c'
        self.ACCENT = '#89b4fa'
        self.GREEN = '#a6e3a1'
        self.ORANGE = '#fab387'
        self.PURPLE = '#cba6f7'
        self.RED = '#f38ba8'
        self.YELLOW = '#f9e2af'

        # State management
        self.state_manager = ScaraState()
        self.ros_node = None
        self._held_keys = set()

        # Playout velocity worker thread
        self.velocity_worker = VelocityStreamingWorker(lambda: self.ros_node)

        # Setup main layouts
        self._apply_style()
        self._setup_ui()

        # Status indicator pulsing animation
        self.pulsator = StatusPulsator(self.led_status, self.RED)
        self.pulsator.start()

        # Thread-safe log signal registration
        self.log_signal.connect(self._log_slot)

        # Main UI update polling timer (running at 30Hz / 33ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_ui)
        self.timer.start(33)

        self._log("PyQt5 Dashboard loaded successfully. Ready to connect to micro-ROS.", 'info')

    def set_ros_node(self, node):
        self.ros_node = node

    def _apply_style(self):
        # Apply comprehensive stylesheet (QSS) for a high-end look
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.BG};
            }}
            QFrame {{
                background-color: transparent;
            }}
            QTabWidget::pane {{
                border: 2px solid #313244;
                background-color: {self.BG_LIGHT};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: #181825;
                color: {self.FG_DIM};
                border: 1px solid #313244;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: bold;
            }}
            QTabBar::tab:selected, QTabBar::tab:hover {{
                background-color: {self.BG_LIGHT};
                color: {self.ACCENT};
                border-bottom: 2px solid {self.ACCENT};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: #45475a;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {self.ACCENT};
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: #11111b;
                width: 10px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #313244;
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
            }}
        """)

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── HEADER BAR ──
        header = QHBoxLayout()
        lbl_title = QLabel("SCARA Robot Dashboard")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {self.ACCENT};")
        header.addWidget(lbl_title)

        lbl_jog_hint = QLabel("Jog: WASD / QE  |  Stop: SPACE  |  Emergency: ESC")
        lbl_jog_hint.setFont(QFont("Segoe UI", 9))
        lbl_jog_hint.setStyleSheet(f"color: {self.FG_DIM};")
        header.addWidget(lbl_jog_hint)
        header.addStretch()

        self.led_status = QLabel()
        self.led_status.setFixedSize(16, 16)
        self.led_status.setStyleSheet("background-color: #3f3f46; border-radius: 8px;")
        header.addWidget(self.led_status)

        self.lbl_conn = QLabel("● Disconnected")
        self.lbl_conn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_conn.setStyleSheet(f"color: {self.RED}; margin-right: 15px;")
        header.addWidget(self.lbl_conn)

        main_layout.addLayout(header)

        # ── 3-COLUMN CONTENT PANEL ──
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        # Left Column (Positions and Manual Jog Pad)
        left_col = QVBoxLayout()
        self.position_panel = PositionPanel(self, self)
        left_col.addWidget(self.position_panel)
        self.jog_panel = JogPanel(self, self)
        left_col.addWidget(self.jog_panel)
        content_layout.addLayout(left_col, 1)

        # Center Column (Tabbed configurations + 2D Paint Simulator Widget)
        center_col = QVBoxLayout()
        center_col.setSpacing(8)

        # Beautiful interactive 2D visualizer widget
        self.visualizer = ScaraVisualizerWidget(self)
        self.visualizer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.visualizer.setMinimumHeight(350)
        center_col.addWidget(self.visualizer, 3)

        tabs = QTabWidget()
        self.target_panel = JointSpacePanel(self, self)
        tabs.addTab(self.target_panel, "Joint Targets")

        self.cartesian_panel = CartesianIKPanel(self, self)
        tabs.addTab(self.cartesian_panel, "Cartesian (IK)")

        self.auto_panel = AutomationLoopPanel(self, self)
        tabs.addTab(self.auto_panel, "Teach & Playback")

        self.servo_panel = ServoPanel(self, self)
        tabs.addTab(self.servo_panel, "Servo control")

        self.config_panel = MotorConfigPanel(self, self)
        tabs.addTab(self.config_panel, "Config Settings")

        center_col.addWidget(tabs, 2)
        content_layout.addLayout(center_col, 2)

        # Right Column (Robot actions / emergency switches and log console)
        right_col = QVBoxLayout()
        self.action_panel = ActionPanel(self, self)
        right_col.addWidget(self.action_panel)

        self.log_panel = LogPanel(self, self)
        right_col.addWidget(self.log_panel)
        content_layout.addLayout(right_col, 1)

        main_layout.addLayout(content_layout)

    # Keyboard Jog Events
    def keyPressEvent(self, event):
        focused = self.focusWidget()
        if isinstance(focused, QLineEdit):
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key_Space or key == Qt.Key_Escape:
            self._emergency()
            return

        if key in self._JOG_KEY_MAP:
            if event.isAutoRepeat():
                return
            self._held_keys.add(key)
            self._recalc_jog()

    def keyReleaseEvent(self, event):
        focused = self.focusWidget()
        if isinstance(focused, QLineEdit):
            super().keyReleaseEvent(event)
            return

        key = event.key()
        if key in self._JOG_KEY_MAP:
            if event.isAutoRepeat():
                return
            self._held_keys.discard(key)
            self._recalc_jog()

    def _recalc_jog(self):
        if not self.ros_node:
            return
        if not self._held_keys:
            self.velocity_worker.set_jog(False)
            return

        # Fetch jog speed multiplier
        spd = self.jog_panel.get_speed()
        vx, vy, vz = 0.0, 0.0, 0.0
        for k in self._held_keys:
            dx, dy, dz = self._JOG_KEY_MAP[k]
            vx += dx * spd
            vy += dy * spd
            vz += dz * spd

        self.velocity_worker.set_jog(True, vx, vy, vz)

    def _jog_start(self, x, y, z):
        if not self.ros_node:
            return
        spd = self.jog_panel.get_speed()
        self.velocity_worker.set_jog(True, x * spd, y * spd, z * spd)

    def _jog_stop(self):
        if not self.ros_node:
            return
        self._held_keys.clear()
        self.velocity_worker.set_jog(False)

    # Action triggers mapped to ROS node
    def _send_cartesian_target(self):
        if not self.ros_node:
            return
        try:
            x_cart = float(self.cartesian_panel.cart_entries['X_mm'][0].text())
            y_cart = float(self.cartesian_panel.cart_entries['Y_mm'][0].text())
            z_mm = float(self.cartesian_panel.cart_entries['Z_mm'][0].text())
            L1 = float(self.cartesian_panel.cart_entries['L1_mm'][0].text())
            L2 = float(self.cartesian_panel.cart_entries['L2_mm'][0].text())
            off1 = float(self.cartesian_panel.cart_entries['Off1_deg'][0].text())
            off2 = float(self.cartesian_panel.cart_entries['Off2_deg'][0].text())
            elbow_up = bool(self.cartesian_panel.elbow_up_var.checkedId())
            
            # Solve Inverse Kinematics analytically
            th1_deg, th2_deg = calculate_inverse_kinematics(x_cart, y_cart, L1, L2, elbow_up)
            
            # Adjust offsets before publishing: target_stepper_angle = physical_angle - offset
            send_th1 = th1_deg - off1
            send_th2 = th2_deg - off2
            
            self.ros_node.send_target(send_th1, send_th2, z_mm)
            self.visualizer.set_target_cartesian(x_cart, y_cart)
            self._log(f"Cartesian Target X={x_cart} Y={y_cart} Z={z_mm} -> Joint1={th1_deg:.2f}° Joint2={th2_deg:.2f}° (Offs: {off1:.1f}°, {off2:.1f}°)", 'success')
            
        except ValueError as ex:
            self._log(f"IK Limit Error: {str(ex)}", 'error')

    def _send_target(self):
        if not self.ros_node:
            return
        try:
            x = float(self.target_panel.target_entries['X_deg'][0].text())
            y = float(self.target_panel.target_entries['Y_deg'][0].text())
            z = float(self.target_panel.target_entries['Z_mm'][0].text())
            self.ros_node.send_target(x, y, z)
            self._log(f"Joint Target sent: X={x:.1f}° Y={y:.1f}° Z={z:.1f}mm", 'info')
        except ValueError:
            self._log("Input Error: Please enter valid numeric values.", 'error')

    def _send_servos(self):
        if not self.ros_node:
            return
        s1 = float(self.servo_panel.s1_slider.value())
        s2 = float(self.servo_panel.s2_slider.value())
        self.ros_node.send_servos(s1, s2)
        self._log(f"Servos set: S1={s1:.0f}° S2={s2:.0f}%", 'info')

    def _send_cmd(self, cmd):
        if not self.ros_node:
            return
        self.ros_node.send_command(cmd)
        tag = 'warning' if cmd == 'HOMING' else 'info'
        self._log(f"Command: {cmd}", tag)

    def _emergency(self):
        self.auto_panel.is_playing = False
        self.auto_panel.is_learning = False
        self._jog_stop()
        if self.ros_node:
            self.ros_node.stop_all()
        self._log("EMERGENCY STOP triggered!", 'error')

    def _send_config(self):
        if not self.ros_node:
            return
        try:
            sx = float(self.config_panel.cfg_vars['Speed X'][0].text())
            ax = float(self.config_panel.cfg_vars['Accel X'][0].text())
            sy = float(self.config_panel.cfg_vars['Speed Y'][0].text())
            ay = float(self.config_panel.cfg_vars['Accel Y'][0].text())
            sz = float(self.config_panel.cfg_vars['Speed Z'][0].text())
            az = float(self.config_panel.cfg_vars['Accel Z'][0].text())
            self.ros_node.send_config(sx, ax, sy, ay, sz, az)
            self._log(f"Config applied: X(spd:{sx:.0f}, acc:{ax:.0f}) Y(spd:{sy:.0f}, acc:{ay:.0f}) Z(spd:{sz:.0f}, acc:{az:.0f})", 'success')
        except ValueError:
            self._log("Config Input Error: Please enter valid numeric values.", 'error')

    # Thread-Safe Logging System
    def _log(self, msg, tag='info'):
        self.log_signal.emit(msg, tag)

    def _log_slot(self, msg, tag):
        ts = time.strftime("%H:%M:%S")
        color_map = {
            'success': self.GREEN,
            'warning': self.ORANGE,
            'error': self.RED,
            'info': self.ACCENT
        }
        color = color_map.get(tag, self.FG)
        html = f"<span style='color: {self.FG_DIM};'>[{ts}]</span> <span style='color: {color};'>{msg}</span>"
        self.log_panel.log_text.append(html)
        # Scroll to bottom
        self.log_panel.log_text.moveCursor(QTextCursor.End)

    def _clear_log(self):
        self.log_panel.log_text.clear()

    # ── Automation Panel Loop Logic ──
    def auto_panel_start_learn(self):
        if self.auto_panel.is_learning:
            return
        if self.auto_panel.is_playing:
            self._log("Cannot learn while trajectory playback is active.", 'error')
            return

        self.auto_panel.recorded_path.clear()
        self.auto_panel.is_learning = True
        
        self.auto_panel.start_learn_btn.setEnabled(False)
        self.auto_panel.stop_learn_btn.setEnabled(True)
        self.auto_panel.start_loop_btn.setEnabled(False)
        
        self.auto_panel.status_lbl.setText("Status: RECORDING")
        self.auto_panel.status_lbl.setStyleSheet(f"color: {self.GREEN}; font-weight: bold;")
        self.auto_panel.points_lbl.setText("Recorded Points: 0")
        self.auto_panel.progress_lbl.setText("Playback Progress: N/A")

        self.learning_thread = threading.Thread(target=self._learning_runner, daemon=True)
        self.learning_thread.start()

    def auto_panel_stop_learn(self):
        if not self.auto_panel.is_learning:
            return
        self.auto_panel.is_learning = False
        
        self.auto_panel.start_learn_btn.setEnabled(True)
        self.auto_panel.stop_learn_btn.setEnabled(False)
        self.auto_panel.start_loop_btn.setEnabled(True)
        
        self.auto_panel.status_lbl.setText("Status: IDLE")
        self.auto_panel.status_lbl.setStyleSheet(f"color: {self.FG};")

    def _learning_runner(self):
        self._log("Learning trajectory started. Move the robot to record points...", 'warning')
        while self.auto_panel.is_learning:
            state = self.state_manager.get_state()
            if state['feedback_received']:
                cp = state['current_pos']
                pt = (cp['x'], cp['y'], cp['z'])
                
                # Deduplicate coordinates while waiting
                if not self.auto_panel.recorded_path or self.auto_panel.recorded_path[-1] != pt:
                    self.auto_panel.recorded_path.append(pt)
                    # Log recorded points
                    self._log(f"Rec Point #{len(self.auto_panel.recorded_path)}: T1={pt[0]:.1f}° T2={pt[1]:.1f}° Z={pt[2]:.1f}mm", 'info')
            time.sleep(0.1)
        self._log(f"Learning stopped. Waypoints: {len(self.auto_panel.recorded_path)}", 'success')

    def auto_panel_start_loop(self):
        if self.auto_panel.is_playing:
            return
        if self.auto_panel.is_learning:
            self._log("Cannot replay while learning is active.", 'error')
            return
        if not self.auto_panel.recorded_path:
            self._log("No recorded path found. Learn a path first.", 'warning')
            return

        self.auto_panel.is_playing = True
        
        self.auto_panel.start_learn_btn.setEnabled(False)
        self.auto_panel.start_loop_btn.setEnabled(False)
        self.auto_panel.stop_loop_btn.setEnabled(True)

        self.playback_thread = threading.Thread(target=self._playback_runner, daemon=True)
        self.playback_thread.start()

    def auto_panel_stop_loop(self):
        if not self.auto_panel.is_playing:
            return
        self.auto_panel.is_playing = False
        self._log("Replay Loop termination requested.", 'warning')

    def _playback_runner(self):
        n_points = len(self.auto_panel.recorded_path)
        self._log(f"Replay sync: Moving to start point...", 'warning')
        start_pt = self.auto_panel.recorded_path[0]
        self.ros_node.send_target(start_pt[0], start_pt[1], start_pt[2])
        
        # Wait for robot to arrive at start coordinates
        time.sleep(0.5)
        timeout = 15.0
        start_t = time.time()
        while time.time() - start_t < timeout:
            if not self.auto_panel.is_playing:
                break
            state = self.state_manager.get_state()
            if state['status'] == 'IDLE':
                break
            time.sleep(0.1)

        self._log("Replay Loop running back-and-forth.", 'success')

        forward = True
        while self.auto_panel.is_playing:
            path_to_run = list(self.auto_panel.recorded_path)
            if not forward:
                path_to_run = list(reversed(self.auto_panel.recorded_path))

            for idx, pt in enumerate(path_to_run):
                if not self.auto_panel.is_playing:
                    break

                self.ros_node.send_target(pt[0], pt[1], pt[2])
                curr_idx = idx + 1 if forward else n_points - idx
                
                # Log execution updates periodically
                if idx % 10 == 0 or idx == len(path_to_run) - 1:
                    self._log(f"Replay Pt {curr_idx}/{n_points}: T1={pt[0]:.1f}° T2={pt[1]:.1f}° Z={pt[2]:.1f}mm", 'info')
                
                time.sleep(0.1)

            forward = not forward

        self._log("Replay Loop ended.", 'info')

    # Main update tick running at 30Hz
    def _update_ui(self):
        state = self.state_manager.get_state()
        connected = state['feedback_received']
        last_ts = state['last_feedback_ts']

        # Determine connection timeout
        if last_ts > 0 and (time.time() - last_ts) > 2.0:
            connected = False

        if connected:
            self.lbl_conn.setText("● Connected")
            self.lbl_conn.setStyleSheet(f"color: {self.GREEN}; margin-right: 15px;")
            self.pulsator.start(self.GREEN)
        else:
            self.lbl_conn.setText("● Disconnected" if last_ts > 0 else "● Waiting for data...")
            self.lbl_conn.setStyleSheet(f"color: {self.RED}; margin-right: 15px;")
            self.pulsator.start(self.RED)

        # Update Status label
        st = state['status']
        color_map = {'IDLE': self.GREEN, 'MOVING': self.YELLOW, 'HOMING': self.ORANGE}
        self.lbl_conn.parent().findChild(QLabel).setStyleSheet(f"color: {color_map.get(st, self.RED)};") # Dynamic style

        cp = state['current_pos']
        tp = state['target_pos']

        # Update position labels
        self.position_panel.pos_labels['X (deg)'].setText(f"X (deg): {cp['x']:>8.2f}")
        self.position_panel.pos_labels['Y (deg)'].setText(f"Y (deg): {cp['y']:>8.2f}")
        self.position_panel.pos_labels['Z (mm)'].setText(f"Z (mm): {cp['z']:>8.2f}")

        # Update target labels
        self.position_panel.target_labels['X (deg)'].setText(f"T:{tp['x']:>7.2f}")
        self.position_panel.target_labels['Y (deg)'].setText(f"T:{tp['y']:>7.2f}")
        self.position_panel.target_labels['Z (mm)'].setText(f"T:{tp['z']:>7.2f}")

        # Smooth slide transitions for progress bars
        try:
            self.position_panel.pos_bars['X (deg)'].animateTo(abs(cp['x']) % 360)
            self.position_panel.pos_bars['Y (deg)'].animateTo(abs(cp['y']) % 360)
            self.position_panel.pos_bars['Z (mm)'].animateTo(min(abs(cp['z']), 100))
        except Exception:
            pass

        # Update 2D SCARA Simulator coordinates and link length configs dynamically
        try:
            L1 = float(self.cartesian_panel.cart_entries['L1_mm'][0].text())
            L2 = float(self.cartesian_panel.cart_entries['L2_mm'][0].text())
            off1 = float(self.cartesian_panel.cart_entries['Off1_deg'][0].text())
            off2 = float(self.cartesian_panel.cart_entries['Off2_deg'][0].text())
            
            # Feed positions and configs to painter visualizer
            self.visualizer.set_joint_angles(cp['x'], cp['y'])
            self.visualizer.set_target_angles(tp['x'], tp['y'])
            self.visualizer.set_geometry(L1, L2, off1, off2)

            # Apply Forward Kinematics to offset-calibrated angles to display actual Cartesian telemetry
            cal_x = cp['x'] + off1
            cal_y = cp['y'] + off2
            x_curr, y_curr = calculate_forward_kinematics(cal_x, cal_y, L1, L2)
            self.position_panel.cart_lbl.setText(f"Cartesian: X = {x_curr:.1f} mm, Y = {y_curr:.1f} mm")
        except Exception:
            pass

        # Update automation loops details
        if self.auto_panel.is_learning:
            self.auto_panel.status_lbl.setText("Status: RECORDING")
            self.auto_panel.status_lbl.setStyleSheet(f"color: {self.GREEN}; font-weight: bold;")
            self.auto_panel.points_lbl.setText(f"Recorded Points: {len(self.auto_panel.recorded_path)}")
        elif self.auto_panel.is_playing:
            self.auto_panel.status_lbl.setText("Status: REPLAYING")
            self.auto_panel.status_lbl.setStyleSheet(f"color: {self.ACCENT}; font-weight: bold;")
            self.auto_panel.points_lbl.setText(f"Recorded Points: {len(self.auto_panel.recorded_path)}")
        else:
            self.auto_panel.status_lbl.setText("Status: IDLE")
            self.auto_panel.status_lbl.setStyleSheet(f"color: {self.FG};")
            self.auto_panel.points_lbl.setText(f"Recorded Points: {len(self.auto_panel.recorded_path)}")

        # Homing Status labels
        hs = state['homing_status']
        hcolor = (self.GREEN if hs == 'SUCCESS' else
                  self.YELLOW if hs == 'RUNNING' else
                  self.RED if hs == 'FAILED' else self.FG_DIM)
        self.action_panel.homing_label.setText(f"Homing: {hs}")
        self.action_panel.homing_label.setStyleSheet(f"color: {hcolor};")

        # Motor State labels
        en = state['motor_en']
        self.action_panel.motor_label.setText(f"Motors: {'ENABLED' if en else 'DISABLED'}")
        self.action_panel.motor_label.setStyleSheet(f"color: {self.GREEN if en else self.RED};")
        self.action_panel.lastcmd_label.setText(f"Last Cmd: {state['last_cmd']}")

    def closeEvent(self, event):
        # Gracefully shut down velocity workers upon close
        self.velocity_worker.stop()
        super().closeEvent(event)


def ros_spin_thread(node):
    rclpy.spin(node)

def main():
    rclpy.init(args=sys.argv)
    
    # PyQt5 high DPI scaling configurations
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    
    scara_app = ScaraApp()
    
    # Initialize ROS Node communication bridge
    node = ScaraRosNode(scara_app.state_manager)
    scara_app.set_ros_node(node)
    
    # Spin ROS node executors in background
    threading.Thread(target=ros_spin_thread, args=(node,), daemon=True).start()
    
    scara_app.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
