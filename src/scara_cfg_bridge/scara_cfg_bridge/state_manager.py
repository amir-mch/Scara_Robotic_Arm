import threading
import time

class ScaraState:
    def __init__(self):
        self._lock = threading.Lock()
        
        # Connection status
        self.feedback_received = False
        self.last_feedback_ts = 0.0
        
        # Position states
        self.current_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.target_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        
        # Action states
        self.status = 'IDLE'
        self.last_cmd = 'NONE'
        self.motor_en = 1
        self.homing_status = 'NONE'

        # Waypoints for automation loop
        self.flag_a = None  # {'x': ..., 'y': ..., 'z': ...}
        self.flag_b = None  # {'x': ..., 'y': ..., 'z': ...}
        self.safe_z = 50.0
        self.cycle_count = 0
        self.automation_active = False

    def update_feedback(self, current_pos, target_pos, status, last_cmd, motor_en):
        with self._lock:
            self.current_pos = current_pos
            self.target_pos = target_pos
            self.status = status
            self.last_cmd = last_cmd
            self.motor_en = motor_en
            self.feedback_received = True
            self.last_feedback_ts = time.time()

    def set_flags(self, flag_a, flag_b, safe_z):
        with self._lock:
            self.flag_a = flag_a
            self.flag_b = flag_b
            self.safe_z = safe_z

    def get_state(self):
        with self._lock:
            return {
                'feedback_received': self.feedback_received,
                'last_feedback_ts': self.last_feedback_ts,
                'current_pos': self.current_pos.copy(),
                'target_pos': self.target_pos.copy(),
                'status': self.status,
                'last_cmd': self.last_cmd,
                'motor_en': self.motor_en,
                'homing_status': self.homing_status,
                'flag_a': self.flag_a.copy() if self.flag_a else None,
                'flag_b': self.flag_b.copy() if self.flag_b else None,
                'safe_z': self.safe_z,
                'cycle_count': self.cycle_count,
                'automation_active': self.automation_active
            }
