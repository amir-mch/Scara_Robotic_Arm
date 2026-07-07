import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from scara_cfg_bridge.kinematics import calculate_forward_kinematics

class AutomationLoopPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.state_manager = app.state_manager
        
        # State variables
        self.recorded_path = []
        self.is_learning = False
        self.is_playing = False
        
        self.learning_thread = None
        self.playback_thread = None

        # Visual layout configuration
        ttk.Label(self, text="Trajectory Learning & Replay",
                  font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W, pady=(0, 6))

        # Instructions
        inst_text = (
            "Instructions:\n"
            "1. Move the robot to the START position using Jog Control.\n"
            "2. Click 'Start Learn' to begin recording.\n"
            "3. Jog the robot along your desired path to the END position.\n"
            "4. Click 'Stop Learn' to finish recording.\n"
            "5. Click 'Start Loop' to play the recorded path back-and-forth."
        )
        ttk.Label(self, text=inst_text, font=('Segoe UI', 9), justify=tk.LEFT,
                  foreground='#7F8C8D', wraplength=350).pack(anchor=tk.W, pady=(0, 10))

        # Status frame
        status_frame = ttk.LabelFrame(self, text=" System Status ", padding=8)
        status_frame.pack(fill=tk.X, pady=6)

        self.status_lbl = ttk.Label(status_frame, text="Status: IDLE", font=('Segoe UI', 10, 'bold'))
        self.status_lbl.pack(anchor=tk.W, pady=2)

        self.points_lbl = ttk.Label(status_frame, text="Recorded Points: 0", font=('Segoe UI', 9))
        self.points_lbl.pack(anchor=tk.W, pady=2)

        self.progress_lbl = ttk.Label(status_frame, text="Playback Progress: N/A", font=('Segoe UI', 9))
        self.progress_lbl.pack(anchor=tk.W, pady=2)

        # Learning Controls
        learn_row = ttk.Frame(self)
        learn_row.pack(fill=tk.X, pady=4)
        
        self.start_learn_btn = ttk.Button(
            learn_row, text="Start Learn", style='Success.TButton', command=self._start_learn
        )
        self.start_learn_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.stop_learn_btn = ttk.Button(
            learn_row, text="Stop Learn", style='Danger.TButton', state=tk.DISABLED, command=self._stop_learn
        )
        self.stop_learn_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Replay Controls
        replay_row = ttk.Frame(self)
        replay_row.pack(fill=tk.X, pady=4)

        self.start_loop_btn = ttk.Button(
            replay_row, text="Start Loop", style='Accent.TButton', command=self._start_loop
        )
        self.start_loop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.stop_loop_btn = ttk.Button(
            replay_row, text="Stop Loop", style='Purple.TButton', state=tk.DISABLED, command=self._stop_loop
        )
        self.stop_loop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def _start_learn(self):
        if self.is_learning:
            return
        if self.is_playing:
            messagebox.showerror("Error", "Cannot learn while trajectory replay is active.")
            return

        self.recorded_path.clear()
        self.is_learning = True
        
        self.start_learn_btn.config(state=tk.DISABLED)
        self.stop_learn_btn.config(state=tk.NORMAL)
        self.start_loop_btn.config(state=tk.DISABLED)
        
        self.status_lbl.config(text="Status: RECORDING", foreground='#2ECC71')
        self.points_lbl.config(text="Recorded Points: 0")
        self.progress_lbl.config(text="Playback Progress: N/A")

        self.learning_thread = threading.Thread(target=self._learning_runner, daemon=True)
        self.learning_thread.start()

    def _stop_learn(self):
        if not self.is_learning:
            return
        self.is_learning = False
        
        self.start_learn_btn.config(state=tk.NORMAL)
        self.stop_learn_btn.config(state=tk.DISABLED)
        self.start_loop_btn.config(state=tk.NORMAL)
        
        self.status_lbl.config(text="Status: IDLE", foreground='#2C3E50')

    def _learning_runner(self):
        self.app._log("Learning trajectory started. Move the robot to record points...", 'warning')
        
        # Read link lengths for logging Cartesian references
        try:
            L1 = float(self.app.cartesian_panel.cart_entries['L1_mm'][0].get())
            L2 = float(self.app.cartesian_panel.cart_entries['L2_mm'][0].get())
        except Exception:
            L1, L2 = 200.0, 150.0  # Safe fallback values for logging

        while self.is_learning:
            state = self.state_manager.get_state()
            if state['feedback_received']:
                cp = state['current_pos']
                pt = (cp['x'], cp['y'], cp['z'])
                
                # Check for duplicates to avoid bloating path list during idle time
                if not self.recorded_path or self.recorded_path[-1] != pt:
                    self.recorded_path.append(pt)
                    count = len(self.recorded_path)
                    self.app.root.after(0, lambda c=count: self.points_lbl.config(text=f"Recorded Points: {c}"))
                    # Log recorded coordinate sample to logs
                    self.app._log(f"Rec Point #{count}: T1={pt[0]:.1f}° T2={pt[1]:.1f}° Z={pt[2]:.1f}mm", 'info')
            
            time.sleep(0.1)  # Record coordinate sample every 100ms
            
        self.app._log(f"Learning trajectory stopped. Total recorded waypoints: {len(self.recorded_path)}", 'success')

    def _start_loop(self):
        if self.is_playing:
            return
        if self.is_learning:
            messagebox.showerror("Error", "Cannot replay while trajectory learning is active.")
            return
        if not self.recorded_path:
            messagebox.showwarning("Warning", "No recorded trajectory found. Please record a path first.")
            return

        self.is_playing = True
        
        self.start_learn_btn.config(state=tk.DISABLED)
        self.start_loop_btn.config(state=tk.DISABLED)
        self.stop_loop_btn.config(state=tk.NORMAL)

        self.playback_thread = threading.Thread(target=self._playback_runner, daemon=True)
        self.playback_thread.start()

    def _stop_loop(self):
        if not self.is_playing:
            return
        self.is_playing = False
        self.app._log("Replay Loop termination requested cleanly.", 'warning')

    def _playback_runner(self):
        n_points = len(self.recorded_path)
        self.app.root.after(0, lambda: self.status_lbl.config(text="Status: SYNCING", foreground='#F39C12'))

        # Step 1: Move robot to starting position of trajectory first
        start_pt = self.recorded_path[0]
        self.app._log(f"Replay sync: Moving to start point T1={start_pt[0]:.1f}° T2={start_pt[1]:.1f}° Z={start_pt[2]:.1f}mm...", 'warning')
        self.app.ros_node.send_target(start_pt[0], start_pt[1], start_pt[2])
        
        # Wait for motion to settle
        time.sleep(0.5)
        timeout = 15.0
        start_t = time.time()
        while time.time() - start_t < timeout:
            if not self.is_playing:
                break
            state = self.state_manager.get_state()
            if state['status'] == 'IDLE':
                break
            time.sleep(0.1)

        self.app.root.after(0, lambda: self.status_lbl.config(text="Status: REPLAYING", foreground='#3498DB'))
        self.app._log("Replay Loop running back-and-forth.", 'success')

        forward = True
        while self.is_playing:
            # Prepare path
            path_to_run = list(self.recorded_path)
            if not forward:
                path_to_run = list(reversed(self.recorded_path))

            for idx, pt in enumerate(path_to_run):
                if not self.is_playing:
                    break

                # Send direct Joint Space coordinates to firmware
                self.app.ros_node.send_target(pt[0], pt[1], pt[2])
                
                # Update GUI
                curr_idx = idx + 1 if forward else n_points - idx
                self.app.root.after(0, lambda i=curr_idx: self.progress_lbl.config(text=f"Playback Progress: Point {i}/{n_points}"))
                
                # Log periodically to monitor trajectory execution values
                if idx % 10 == 0 or idx == len(path_to_run) - 1:
                    self.app._log(f"Replay Pt {curr_idx}/{n_points}: T1={pt[0]:.1f}° T2={pt[1]:.1f}° Z={pt[2]:.1f}mm", 'info')
                
                time.sleep(0.1) # Match 100ms record interval

            # Flip direction for back-and-forth replay
            forward = not forward

        # Post-loop cleanup
        self.app.root.after(0, lambda: self.status_lbl.config(text="Status: IDLE", foreground='#2C3E50'))
        self.app.root.after(0, lambda: self.progress_lbl.config(text="Playback Progress: N/A"))
        
        self.start_learn_btn.config(state=tk.NORMAL)
        self.start_loop_btn.config(state=tk.NORMAL)
        self.stop_loop_btn.config(state=tk.DISABLED)
        
        self.app._log("Replay Loop ended.", 'info')
