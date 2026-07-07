from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QLineEdit, QSlider, QRadioButton, QButtonGroup, QPushButton, 
    QGroupBox, QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QTextCursor, QTextCharFormat
from scara_cfg_bridge.gui_animations import AnimatedProgressBar

class PositionPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Current Position  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(10)
        
        self.pos_labels = {}
        self.pos_bars = {}
        self.target_labels = {}
        
        axis_cfg = [
            ('X (deg)', '#89b4fa', 360),
            ('Y (deg)', '#a6e3a1', 360),
            ('Z (mm)',  '#fab387', 100),
        ]
        
        for axis, color, rng in axis_cfg:
            row = QHBoxLayout()
            
            lbl = QLabel(f"{axis}:  0.00")
            lbl.setFont(QFont("Consolas", 11, QFont.Bold))
            lbl.setStyleSheet(f"color: {color};")
            lbl.setMinimumWidth(150)
            row.addWidget(lbl)
            
            bar = AnimatedProgressBar()
            bar.setRange(0, int(rng))
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            # Style custom bar color
            bar_color = color
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #45475a;
                    border-radius: 6px;
                    background-color: #11111b;
                }}
                QProgressBar::chunk {{
                    background-color: {bar_color};
                    border-radius: 5px;
                }}
            """)
            row.addWidget(bar)
            
            tgt_lbl = QLabel("T: 0.00")
            tgt_lbl.setFont(QFont("Consolas", 10))
            tgt_lbl.setStyleSheet("color: #7f849c;")
            tgt_lbl.setMinimumWidth(80)
            tgt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(tgt_lbl)
            
            layout.addLayout(row)
            
            self.pos_labels[axis] = lbl
            self.pos_bars[axis] = bar
            self.target_labels[axis] = tgt_lbl
            
        # Draw Cartesian coordinate status label at bottom
        self.cart_lbl = QLabel("Cartesian: X = 0.0 mm, Y = 0.0 mm")
        self.cart_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.cart_lbl.setStyleSheet("color: #89dceb; padding-top: 5px;")
        layout.addWidget(self.cart_lbl)
        
        self.setLayout(layout)


class JogPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Jog Control (WASD / QE / SPACE)  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        
        # Speed slider row
        spd_row = QHBoxLayout()
        lbl_spd = QLabel("Speed:")
        lbl_spd.setFont(QFont("Segoe UI", 9))
        lbl_spd.setStyleSheet("color: #bac2de;")
        spd_row.addWidget(lbl_spd)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 800) # representing 0.1 to 80.0
        self.slider.setValue(200) # default 20.0
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #313244;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #89b4fa;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #b4befe;
            }
        """)
        spd_row.addWidget(self.slider)
        
        self.lbl_spd_val = QLabel("20.0")
        self.lbl_spd_val.setFont(QFont("Consolas", 10, QFont.Bold))
        self.lbl_spd_val.setStyleSheet("color: #89b4fa; min-width: 40px;")
        self.lbl_spd_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        spd_row.addWidget(self.lbl_spd_val)
        self.slider.valueChanged.connect(self._on_speed_changed)
        
        layout.addLayout(spd_row)
        
        # Button pad (grid layout)
        pad = QGridLayout()
        pad.setSpacing(6)
        
        # We bind button press/release triggers cleanly
        self.btn_y_up = QPushButton("Y+ (W)")
        self.btn_y_up.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_y_up.pressed.connect(lambda: app._jog_start(0, 1, 0))
        self.btn_y_up.released.connect(app._jog_stop)
        pad.addWidget(self.btn_y_up, 0, 1)
        
        self.btn_x_left = QPushButton("X- (A)")
        self.btn_x_left.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_x_left.pressed.connect(lambda: app._jog_start(-1, 0, 0))
        self.btn_x_left.released.connect(app._jog_stop)
        pad.addWidget(self.btn_x_left, 1, 0)
        
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_stop.setStyleSheet(self._btn_style("#f38ba8", "#eba0b2", "#11111b"))
        self.btn_stop.clicked.connect(app._jog_stop)
        pad.addWidget(self.btn_stop, 1, 1)
        
        self.btn_x_right = QPushButton("X+ (D)")
        self.btn_x_right.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_x_right.pressed.connect(lambda: app._jog_start(1, 0, 0))
        self.btn_x_right.released.connect(app._jog_stop)
        pad.addWidget(self.btn_x_right, 1, 2)
        
        self.btn_y_down = QPushButton("Y- (S)")
        self.btn_y_down.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_y_down.pressed.connect(lambda: app._jog_start(0, -1, 0))
        self.btn_y_down.released.connect(app._jog_stop)
        pad.addWidget(self.btn_y_down, 2, 1)
        
        layout.addLayout(pad)
        
        # Z heights buttons row
        z_row = QHBoxLayout()
        z_row.setSpacing(6)
        
        self.btn_z_up = QPushButton("Z+ (Q)")
        self.btn_z_up.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_z_up.pressed.connect(lambda: app._jog_start(0, 0, 1))
        self.btn_z_up.released.connect(app._jog_stop)
        z_row.addWidget(self.btn_z_up)
        
        self.btn_z_down = QPushButton("Z- (E)")
        self.btn_z_down.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_z_down.pressed.connect(lambda: app._jog_start(0, 0, -1))
        self.btn_z_down.released.connect(app._jog_stop)
        z_row.addWidget(self.btn_z_down)
        
        layout.addLayout(z_row)
        self.setLayout(layout)
        
    def _on_speed_changed(self, val):
        self.lbl_spd_val.setText(f"{val/10.0:.1f}")
        
    def _btn_style(self, bg, hover, fg="#cdd6f4"):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 6px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: #1e1e2e;
                padding-left: 8px;
                padding-top: 8px;
            }}
        """

    def get_speed(self):
        return self.slider.value() / 10.0


class JointSpacePanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Joint Space Targets  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        
        self.target_entries = {}
        
        axis_cfg = [
            ('X_deg', 'X (deg):', 0, 360, 0.0),
            ('Y_deg', 'Y (deg):', -180, 180, 0.0),
            ('Z_mm',  'Z (mm):',  0, 100, 0.0),
        ]
        
        for key, label_text, lo, hi, default in axis_cfg:
            row = QHBoxLayout()
            
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setMinimumWidth(60)
            row.addWidget(lbl)
            
            entry = QLineEdit(str(default))
            entry.setFont(QFont("Consolas", 10))
            entry.setFixedWidth(60)
            entry.setStyleSheet("""
                QLineEdit {
                    background-color: #11111b;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 3px;
                }
                QLineEdit:focus {
                    border: 1px solid #89b4fa;
                }
            """)
            row.addWidget(entry)
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(lo), int(hi))
            slider.setValue(int(default))
            slider.setStyleSheet("""
                QSlider::groove:horizontal { height: 4px; background: #313244; border-radius: 2px; }
                QSlider::handle:horizontal { background: #cba6f7; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
            """)
            row.addWidget(slider)
            
            # Sync slider and entry box
            slider.valueChanged.connect(lambda v, e=entry: e.setText(str(v)))
            entry.textChanged.connect(lambda txt, s=slider, l=lo, h=hi: self._sync_slider(txt, s, l, h))
            
            layout.addLayout(row)
            self.target_entries[key] = (entry, slider, None)
            
        self.btn_send = QPushButton("▶  Send Joint Target Position")
        self.btn_send.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border: 1px solid #74c7ec;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton:pressed { background-color: #74c7ec; }
        """)
        self.btn_send.clicked.connect(app._send_target)
        layout.addWidget(self.btn_send)
        
        self.setLayout(layout)
        
    def _sync_slider(self, txt, slider, lo, hi):
        try:
            val = int(float(txt))
            if lo <= val <= hi:
                slider.blockSignals(True)
                slider.setValue(val)
                slider.blockSignals(False)
        except ValueError:
            pass


class CartesianIKPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Cartesian Target (IK)  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)
        
        self.cart_entries = {}
        
        # Link lengths config row
        link_row = QHBoxLayout()
        link_row.addWidget(QLabel("L1 (mm):"))
        e_l1 = QLineEdit("200.0")
        self._style_entry(e_l1)
        link_row.addWidget(e_l1)
        
        link_row.addWidget(QLabel("L2 (mm):"))
        e_l2 = QLineEdit("150.0")
        self._style_entry(e_l2)
        link_row.addWidget(e_l2)
        layout.addLayout(link_row)
        
        self.cart_entries['L1_mm'] = (e_l1, None, None)
        self.cart_entries['L2_mm'] = (e_l2, None, None)
        
        # Calibration offset row
        offset_row = QHBoxLayout()
        offset_row.addWidget(QLabel("Off1 (deg):"))
        e_off1 = QLineEdit("0.0")
        self._style_entry(e_off1)
        offset_row.addWidget(e_off1)
        
        offset_row.addWidget(QLabel("Off2 (deg):"))
        e_off2 = QLineEdit("0.0")
        self._style_entry(e_off2)
        offset_row.addWidget(e_off2)
        layout.addLayout(offset_row)
        
        self.cart_entries['Off1_deg'] = (e_off1, None, None)
        self.cart_entries['Off2_deg'] = (e_off2, None, None)
        
        # Cartesian inputs (X, Y, Z coordinates)
        axis_cfg = [
            ('X_mm', 'X (mm):', -350, 350, 0.0),
            ('Y_mm', 'Y (mm):', -350, 350, 0.0),
            ('Z_mm', 'Z (mm):', 0, 100, 0.0),
        ]
        
        for key, label_text, lo, hi, default in axis_cfg:
            row = QHBoxLayout()
            
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setMinimumWidth(60)
            row.addWidget(lbl)
            
            entry = QLineEdit(str(default))
            entry.setFont(QFont("Consolas", 10))
            entry.setFixedWidth(60)
            self._style_entry(entry)
            row.addWidget(entry)
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(lo), int(hi))
            slider.setValue(int(default))
            slider.setStyleSheet("""
                QSlider::groove:horizontal { height: 4px; background: #313244; border-radius: 2px; }
                QSlider::handle:horizontal { background: #fab387; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
            """)
            row.addWidget(slider)
            
            # Sync slider and entry box
            slider.valueChanged.connect(lambda v, e=entry: e.setText(str(val:=float(v))))
            entry.textChanged.connect(lambda txt, s=slider, l=lo, h=hi: self._sync_slider(txt, s, l, h))
            
            layout.addLayout(row)
            self.cart_entries[key] = (entry, slider, None)
            
        # Elbow UP/DOWN radio configuration
        elbow_row = QHBoxLayout()
        self.btn_up = QRadioButton("Elbow UP")
        self.btn_up.setChecked(True)
        self.btn_up.setStyleSheet("color: #cdd6f4;")
        self.btn_down = QRadioButton("Elbow DOWN")
        self.btn_down.setStyleSheet("color: #cdd6f4;")
        
        self.elbow_up_var = QButtonGroup(self)
        self.elbow_up_var.addButton(self.btn_up, 1)
        self.elbow_up_var.addButton(self.btn_down, 0)
        
        elbow_row.addWidget(self.btn_up)
        elbow_row.addWidget(self.btn_down)
        layout.addLayout(elbow_row)
        
        # Apply button
        self.btn_apply = QPushButton("⚡  Apply Cartesian Target (IK)")
        self.btn_apply.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #11111b;
                border: 1px solid #94e2d5;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton:pressed { background-color: #94e2d5; }
        """)
        self.btn_apply.clicked.connect(app._send_cartesian_target)
        layout.addWidget(self.btn_apply)
        
        self.setLayout(layout)
        
    def _style_entry(self, entry):
        entry.setFont(QFont("Consolas", 10))
        entry.setStyleSheet("""
            QLineEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #fab387;
            }
        """)

    def _sync_slider(self, txt, slider, lo, hi):
        try:
            val = int(float(txt))
            if lo <= val <= hi:
                slider.blockSignals(True)
                slider.setValue(val)
                slider.blockSignals(False)
                # Update arm simulator target point dynamically
                if self.cart_entries['X_mm'][0] is not None:
                    try:
                        x = float(self.cart_entries['X_mm'][0].get() if hasattr(self.cart_entries['X_mm'][0], 'get') else self.cart_entries['X_mm'][0].text())
                        y = float(self.cart_entries['Y_mm'][0].get() if hasattr(self.cart_entries['Y_mm'][0], 'get') else self.cart_entries['Y_mm'][0].text())
                        self.app.visualizer.set_target_cartesian(x, y)
                    except Exception:
                        pass
        except ValueError:
            pass


class ServoPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Servo Control  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(8)
        
        # Servo 1
        s1_row = QHBoxLayout()
        s1_row.addWidget(QLabel("Servo 1 Wrist (-90..90):"))
        self.s1_val = QLabel("0")
        self.s1_val.setFont(QFont("Consolas", 10, QFont.Bold))
        self.s1_val.setStyleSheet("color: #cba6f7;")
        s1_row.addWidget(self.s1_val)
        layout.addLayout(s1_row)
        
        self.s1_slider = QSlider(Qt.Horizontal)
        self.s1_slider.setRange(-90, 90)
        self.s1_slider.setValue(0)
        self.s1_slider.valueChanged.connect(lambda v: self.s1_val.setText(str(v)))
        self.s1_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #313244; }
            QSlider::handle:horizontal { background: #cba6f7; width: 12px; border-radius: 6px; }
        """)
        layout.addWidget(self.s1_slider)
        
        # Servo 2
        s2_row = QHBoxLayout()
        s2_row.addWidget(QLabel("Servo 2 Gripper (0..100):"))
        self.s2_val = QLabel("0")
        self.s2_val.setFont(QFont("Consolas", 10, QFont.Bold))
        self.s2_val.setStyleSheet("color: #cba6f7;")
        s2_row.addWidget(self.s2_val)
        layout.addLayout(s2_row)
        
        self.s2_slider = QSlider(Qt.Horizontal)
        self.s2_slider.setRange(0, 100)
        self.s2_slider.setValue(0)
        self.s2_slider.valueChanged.connect(lambda v: self.s2_val.setText(str(v)))
        self.s2_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #313244; }
            QSlider::handle:horizontal { background: #cba6f7; width: 12px; border-radius: 6px; }
        """)
        layout.addWidget(self.s2_slider)
        
        self.btn_set = QPushButton("Set Servos")
        self.btn_set.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_set.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #11111b;
                border: 1px solid #f5c2e7;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #f5c2e7; }
        """)
        self.btn_set.clicked.connect(app._send_servos)
        layout.addWidget(self.btn_set)
        
        self.setLayout(layout)


class MotorConfigPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Motor Speed / Accel  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)
        
        self.cfg_vars = {}
        cfg_items = [
            ('Speed X',  8000,  100, 20000),
            ('Accel X',  5000,  100, 15000),
            ('Speed Y', 12000,  100, 25000),
            ('Accel Y',  5000,  100, 15000),
            ('Speed Z',  8000,  100, 20000),
            ('Accel Z',  5000,  100, 15000),
        ]
        
        for name, val, lo, hi in cfg_items:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"))
            
            entry = QLineEdit(str(val))
            entry.setFont(QFont("Consolas", 10))
            entry.setFixedWidth(60)
            entry.setStyleSheet("""
                QLineEdit {
                    background-color: #11111b;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 2px;
                }
            """)
            row.addWidget(entry)
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(lo, hi)
            slider.setValue(val)
            slider.setStyleSheet("""
                QSlider::groove:horizontal { height: 4px; background: #313244; }
                QSlider::handle:horizontal { background: #b4befe; width: 10px; border-radius: 5px; }
            """)
            row.addWidget(slider)
            
            slider.valueChanged.connect(lambda v, e=entry: e.setText(str(v)))
            
            layout.addLayout(row)
            self.cfg_vars[name] = (entry, slider, None)
            
        self.btn_apply = QPushButton("Apply Config Updates")
        self.btn_apply.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #b4befe;
                color: #11111b;
                border: 1px solid #74c7ec;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton:hover { background-color: #89b4fa; }
        """)
        self.btn_apply.clicked.connect(app._send_config)
        layout.addWidget(self.btn_apply)
        
        self.setLayout(layout)


class ActionPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Actions  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)
        
        self.homing_label = QLabel("Homing: NONE")
        self.homing_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self.homing_label)
        
        self.motor_label = QLabel("Motors: ENABLED")
        self.motor_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self.motor_label)
        
        self.lastcmd_label = QLabel("Last Cmd: NONE")
        self.lastcmd_label.setFont(QFont("Segoe UI", 9))
        self.lastcmd_label.setStyleSheet("color: #7f849c;")
        layout.addWidget(self.lastcmd_label)
        
        # Action Buttons
        self.btn_home = QPushButton("🏠  Start Homing Sequence")
        self.btn_home.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_home.setStyleSheet(self._btn_style("#fab387", "#f9e2af", "#11111b"))
        self.btn_home.clicked.connect(lambda: app._send_cmd("HOMING"))
        layout.addWidget(self.btn_home)
        
        self.btn_enable = QPushButton("Enable Motors")
        self.btn_enable.setStyleSheet(self._btn_style("#a6e3a1", "#94e2d5", "#11111b"))
        self.btn_enable.clicked.connect(lambda: app._send_cmd("RESET"))
        layout.addWidget(self.btn_enable)
        
        self.btn_disable = QPushButton("Disable Motors")
        self.btn_disable.setStyleSheet(self._btn_style("#45475a", "#585b70"))
        self.btn_disable.clicked.connect(lambda: app._send_cmd("EMERGENCY_STOP"))
        layout.addWidget(self.btn_disable)
        
        self.btn_stop = QPushButton("🛑 EMERGENCY STOP 🛑")
        self.btn_stop.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_stop.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.btn_stop.setMinimumHeight(45)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #11111b;
                border: 2px solid #ef4444;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #ef4444; }
            QPushButton:pressed { background-color: #991b1b; }
        """)
        self.btn_stop.clicked.connect(app._emergency)
        layout.addWidget(self.btn_stop)
        
        self.setLayout(layout)
        
    def _btn_style(self, bg, hover, fg="#cdd6f4"):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 6px;
                padding: 6px;
                min-height: 24px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """


class LogPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  System Log Console  ", parent)
        self.app = app
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.log_text)
        
        self.btn_clear = QPushButton("Clear Logs")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover { background-color: #585b70; }
        """)
        self.btn_clear.clicked.connect(app._clear_log)
        layout.addWidget(self.btn_clear)
        
        self.setLayout(layout)


class AutomationLoopPanel(QGroupBox):
    def __init__(self, parent, app):
        super().__init__("  Trajectory Teach & Playback  ", parent)
        self.app = app
        self.state_manager = app.state_manager
        
        self.recorded_path = []
        self.is_learning = False
        self.is_playing = False
        
        self.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #313244;
                border-radius: 10px;
                margin-top: 10px;
                color: #cdd6f4;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)
        
        inst = QLabel(
            "Instructions:\n"
            "1. Jog to the START position.\n"
            "2. Click 'Start Learn' to record.\n"
            "3. Jog robot along your path to the END position.\n"
            "4. Click 'Stop Learn'.\n"
            "5. Click 'Start Loop' for back-and-forth playback."
        )
        inst.setFont(QFont("Segoe UI", 9))
        inst.setStyleSheet("color: #7f849c;")
        inst.setWordWrap(True)
        layout.addWidget(inst)
        
        # Status rows
        self.status_lbl = QLabel("Status: IDLE")
        self.status_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(self.status_lbl)
        
        self.points_lbl = QLabel("Recorded Points: 0")
        self.points_lbl.setFont(QFont("Segoe UI", 9))
        self.points_lbl.setStyleSheet("color: #bac2de;")
        layout.addWidget(self.points_lbl)
        
        self.progress_lbl = QLabel("Playback Progress: N/A")
        self.progress_lbl.setFont(QFont("Segoe UI", 9))
        self.progress_lbl.setStyleSheet("color: #bac2de;")
        layout.addWidget(self.progress_lbl)
        
        # Buttons
        btn_row1 = QHBoxLayout()
        self.start_learn_btn = QPushButton("Start Learn")
        self.start_learn_btn.setStyleSheet(self._btn_style("#a6e3a1", "#94e2d5", "#11111b"))
        self.start_learn_btn.clicked.connect(self._start_learn)
        btn_row1.addWidget(self.start_learn_btn)
        
        self.stop_learn_btn = QPushButton("Stop Learn")
        self.stop_learn_btn.setEnabled(False)
        self.stop_learn_btn.setStyleSheet(self._btn_style("#f38ba8", "#eba0b2", "#11111b"))
        self.stop_learn_btn.clicked.connect(self._stop_learn)
        btn_row1.addWidget(self.stop_learn_btn)
        layout.addLayout(btn_row1)
        
        btn_row2 = QHBoxLayout()
        self.start_loop_btn = QPushButton("Start Loop")
        self.start_loop_btn.setStyleSheet(self._btn_style("#89b4fa", "#b4befe", "#11111b"))
        self.start_loop_btn.clicked.connect(self._start_loop)
        btn_row2.addWidget(self.start_loop_btn)
        
        self.stop_loop_btn = QPushButton("Stop Loop")
        self.stop_loop_btn.setEnabled(False)
        self.stop_loop_btn.setStyleSheet(self._btn_style("#cba6f7", "#f5c2e7", "#11111b"))
        self.stop_loop_btn.clicked.connect(self._stop_loop)
        btn_row2.addWidget(self.stop_loop_btn)
        layout.addLayout(btn_row2)
        
        self.setLayout(layout)
        
    def _btn_style(self, bg, hover, fg="#cdd6f4"):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:disabled {{ background-color: #313244; color: #585b70; }}
        """

    def _start_learn(self):
        self.app.auto_panel_start_learn()

    def _stop_learn(self):
        self.app.auto_panel_stop_learn()

    def _start_loop(self):
        self.app.auto_panel_start_loop()

    def _stop_loop(self):
        self.app.auto_panel_stop_loop()
