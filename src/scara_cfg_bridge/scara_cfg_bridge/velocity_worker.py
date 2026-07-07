import time
import threading

class VelocityStreamingWorker:
    def __init__(self, ros_node_getter):
        """
        :param ros_node_getter: A callable that returns the active ros_node,
                                or None if not initialized yet.
        """
        self.ros_node_getter = ros_node_getter
        self.jog_active = False
        self.jog_vel = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.active = True
        self._lock = threading.Lock()
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def set_jog(self, active, x_vel=0.0, y_vel=0.0, z_vel=0.0):
        with self._lock:
            self.jog_active = active
            self.jog_vel = {'x': x_vel, 'y': y_vel, 'z': z_vel}

    def stop(self):
        self.active = False
        self.thread.join(timeout=1.0)

    def _run(self):
        interval = 0.030  # 30 ms
        decel_steps = 6
        decel_counter = 0
        last_active_vel = {'x': 0.0, 'y': 0.0, 'z': 0.0}

        while self.active:
            start_time = time.time()
            with self._lock:
                jog_active = self.jog_active
                jog_vel = self.jog_vel.copy()

            ros_node = self.ros_node_getter()

            if jog_active:
                if ros_node:
                    ros_node.send_velocity(jog_vel['x'], jog_vel['y'], jog_vel['z'])
                last_active_vel = jog_vel.copy()
                decel_counter = decel_steps
            elif decel_counter > 0:
                factor = decel_counter / float(decel_steps)
                vx = last_active_vel['x'] * factor
                vy = last_active_vel['y'] * factor
                vz = last_active_vel['z'] * factor

                if abs(vx) < 0.05 and abs(vy) < 0.05 and abs(vz) < 0.05:
                    vx, vy, vz = 0.0, 0.0, 0.0
                    decel_counter = 0
                else:
                    decel_counter -= 1

                if ros_node:
                    ros_node.send_velocity(vx, vy, vz)

            elapsed = time.time() - start_time
            sleep_time = max(0.001, interval - elapsed)
            time.sleep(sleep_time)
