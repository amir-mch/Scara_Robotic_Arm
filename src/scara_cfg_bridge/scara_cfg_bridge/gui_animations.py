import math
from collections import deque
from PyQt5.QtWidgets import QWidget, QProgressBar
from PyQt5.QtCore import QObject, QVariantAnimation, QAbstractAnimation, QEasingCurve, QPointF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF, QRadialGradient

class StatusPulsator(QObject):
    def __init__(self, target_widget, base_color_hex="#10b981"):
        super().__init__()
        self.target = target_widget
        self.base_color = QColor(base_color_hex)
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.2)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(1000)
        self.animation.setDirection(QAbstractAnimation.Forward)
        self.animation.setLoopCount(-1)
        self.animation.currentLoopChanged.connect(self._toggle_direction)
        self.animation.valueChanged.connect(self._apply_style)
        self.active = False

    def _toggle_direction(self, loop):
        if self.animation.direction() == QAbstractAnimation.Forward:
            self.animation.setDirection(QAbstractAnimation.Backward)
        else:
            self.animation.setDirection(QAbstractAnimation.Forward)

    def _apply_style(self, value):
        if not self.active:
            return
        color_str = f"rgba({self.base_color.red()}, {self.base_color.green()}, {self.base_color.blue()}, {value:.2f})"
        border_color_str = f"rgba({self.base_color.red()}, {self.base_color.green()}, {self.base_color.blue()}, 0.8)"
        self.target.setStyleSheet(f"""
            QLabel {{
                background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, 
                    stop:0 {color_str}, stop:0.8 {color_str}, stop:1 rgba(0,0,0,0));
                border: 2px solid {border_color_str};
                border-radius: 8px;
            }}
        """)

    def start(self, color_hex=None):
        if color_hex:
            self.base_color = QColor(color_hex)
        self.active = True
        if self.animation.state() != QAbstractAnimation.Running:
            self.animation.start()

    def stop(self):
        self.active = False
        self.animation.stop()
        self.target.setStyleSheet("QLabel { background-color: #3f3f46; border: 2px solid #52525b; border-radius: 8px; }")


class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.valueChanged.connect(self._setValueDirect)

    def _setValueDirect(self, val):
        super().setValue(int(val))

    def animateTo(self, target_value):
        self.anim.stop()
        self.anim.setStartValue(self.value())
        self.anim.setEndValue(target_value)
        self.anim.start()


class ScaraVisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theta1 = 0.0
        self.theta2 = 0.0
        self.target_theta1 = 0.0
        self.target_theta2 = 0.0
        
        self.L1 = 200.0
        self.L2 = 150.0
        self.off1 = 0.0
        self.off2 = 0.0
        
        # Smooth tracking positions
        self.curr_theta1 = 0.0
        self.curr_theta2 = 0.0
        
        # End effector path history
        self.trail = deque(maxlen=80)
        self.target_pt = None  # (x, y) target coordinate in mm
        
        # Animation timer (60 FPS redraw / smooth interpolation)
        self.startTimer(16)

    def timerEvent(self, event):
        # Apply exponential smoothing filter for fluid movement on UI
        alpha = 0.15
        self.curr_theta1 += alpha * (self.theta1 - self.curr_theta1)
        self.curr_theta2 += alpha * (self.theta2 - self.curr_theta2)
        
        # Calculate current Cartesian coordinates to append to path trail
        th1_r = math.radians(self.curr_theta1 + self.off1)
        th2_r = math.radians(self.curr_theta2 + self.off2)
        x = self.L1 * math.cos(th1_r) + self.L2 * math.cos(th1_r + th2_r)
        y = self.L1 * math.sin(th1_r) + self.L2 * math.sin(th1_r + th2_r)
        
        # Append unique trail points to avoid visual bloat
        pt = QPointF(x, y)
        if not self.trail or (self.trail[-1] - pt).manhattanLength() > 1.0:
            self.trail.append(pt)
            
        self.update()

    def set_joint_angles(self, t1, t2):
        self.theta1 = t1
        self.theta2 = t2

    def set_target_angles(self, t1, t2):
        self.target_theta1 = t1
        self.target_theta2 = t2

    def set_geometry(self, l1, l2, off1, off2):
        self.L1 = l1
        self.L2 = l2
        self.off1 = off1
        self.off2 = off2

    def set_target_cartesian(self, x, y):
        self.target_pt = (x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear screen with dark backdrop
        painter.fillRect(self.rect(), QColor("#1e1e2e"))
        
        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2
        
        # Determine scaling factors
        max_reach = self.L1 + self.L2
        scale = (min(w, h) / 2 * 0.85) / max(100.0, max_reach)
        
        # 1. Draw grid lines
        grid_pen = QPen(QColor("#313244"), 1, Qt.DashLine)
        painter.setPen(grid_pen)
        grid_interval = 50.0  # every 50mm
        
        # Vertical grid guides
        max_grid_count = int(max_reach / grid_interval) + 1
        for i in range(-max_grid_count, max_grid_count + 1):
            offset = i * grid_interval * scale
            painter.drawLine(int(cx + offset), 0, int(cx + offset), h)
            painter.drawLine(0, int(cy + offset), w, int(cy + offset))
            
        # Draw base coordinate axes
        axis_pen = QPen(QColor("#45475a"), 1.5, Qt.SolidLine)
        painter.setPen(axis_pen)
        painter.drawLine(int(cx), 0, int(cx), h)
        painter.drawLine(0, int(cy), w, int(cy))
        
        # 2. Paint Trail / Path history
        if len(self.trail) > 1:
            trail_pen = QPen(QColor("#89b4fa"), 2, Qt.SolidLine)
            painter.setPen(trail_pen)
            for i in range(len(self.trail) - 1):
                p1 = self.trail[i]
                p2 = self.trail[i+1]
                
                # Apply alpha gradient fading to oldest points
                opacity = int((i / len(self.trail)) * 255)
                trail_color = QColor("#89b4fa")
                trail_color.setAlpha(opacity)
                painter.setPen(QPen(trail_color, 2, Qt.SolidLine, Qt.RoundCap))
                
                s1_x = cx + p1.x() * scale
                s1_y = cy - p1.y() * scale
                s2_x = cx + p2.x() * scale
                s2_y = cy - p2.y() * scale
                painter.drawLine(QPointF(s1_x, s1_y), QPointF(s2_x, s2_y))

        # 3. Draw target crosshair (if present)
        if self.target_pt:
            tx, ty = self.target_pt
            ts_x = cx + tx * scale
            ts_y = cy - ty * scale
            target_pen = QPen(QColor("#f38ba8"), 1.5, Qt.SolidLine)
            painter.setPen(target_pen)
            painter.drawEllipse(QPointF(ts_x, ts_y), 6, 6)
            painter.drawLine(int(ts_x - 10), int(ts_y), int(ts_x + 10), int(ts_y))
            painter.drawLine(int(ts_x), int(ts_y - 10), int(ts_x), int(ts_y + 10))

        # 4. Compute Joint Positions for current (moving) position
        t1_r = math.radians(self.curr_theta1 + self.off1)
        t2_r = math.radians(self.curr_theta2 + self.off2)
        
        j1_x = self.L1 * math.cos(t1_r)
        j1_y = self.L1 * math.sin(t1_r)
        j2_x = j1_x + self.L2 * math.cos(t1_r + t2_r)
        j2_y = j1_y + self.L2 * math.sin(t1_r + t2_r)
        
        # Screen positions
        s_base = QPointF(cx, cy)
        s_j1 = QPointF(cx + j1_x * scale, cy - j1_y * scale)
        s_j2 = QPointF(cx + j2_x * scale, cy - j2_y * scale)
        
        # 5. Draw Arm links
        # Link 1 (Shoulder to Elbow)
        link1_pen = QPen(QColor("#cba6f7"), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(link1_pen)
        painter.drawLine(s_base, s_j1)
        
        # Link 2 (Elbow to End Effector)
        link2_pen = QPen(QColor("#a6e3a1"), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(link2_pen)
        painter.drawLine(s_j1, s_j2)
        
        # 6. Draw Joints (Pedestal, Elbow, Tool)
        # Base origin
        painter.setPen(QPen(QColor("#f9e2af"), 2))
        painter.setBrush(QBrush(QColor("#313244")))
        painter.drawEllipse(s_base, 12, 12)
        painter.drawEllipse(s_base, 4, 4)
        
        # Elbow Joint
        painter.setPen(QPen(QColor("#fab387"), 2))
        painter.setBrush(QBrush(QColor("#1e1e2e")))
        painter.drawEllipse(s_j1, 8, 8)
        
        # End Effector (Tool Center Point)
        painter.setPen(QPen(QColor("#89dceb"), 2))
        painter.setBrush(QBrush(QColor("#89dceb")))
        painter.drawEllipse(s_j2, 6, 6)
        
        # Radial glow around TCP
        glow_grad = QRadialGradient(s_j2, 18)
        glow_grad.setColorAt(0, QColor(137, 220, 235, 120))
        glow_grad.setColorAt(1, QColor(137, 220, 235, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_grad))
        painter.drawEllipse(s_j2, 18, 18)
