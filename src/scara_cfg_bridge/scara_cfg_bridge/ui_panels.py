import tkinter as tk
from tkinter import ttk, messagebox

class BasePanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

class PositionPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Current Position",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 4))

        self.pos_labels = {}
        self.pos_bars   = {}
        self.target_labels = {}

        axis_cfg = [
            ('X (deg)', app.ACCENT,  app.GREEN,  360),
            ('Y (deg)', app.GREEN,   app.ORANGE, 360),
            ('Z (mm)',  app.ORANGE,  app.PURPLE, 100),
        ]
        for axis, color, bar_color, rng in axis_cfg:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)

            lbl = ttk.Label(row, text=f"{axis}:  0.00",
                            font=('Consolas', 11, 'bold'), foreground=color, width=22)
            lbl.pack(side=tk.LEFT)

            tgt_lbl = ttk.Label(row, text=f"T: 0.00",
                                font=('Consolas', 9), foreground=app.FG_DIM, width=10)
            tgt_lbl.pack(side=tk.RIGHT, padx=(0, 4))

            pbar_style = 'Horizontal.TProgressbar'
            if 'Y' in axis: pbar_style = 'Green.Horizontal.TProgressbar'
            if 'Z' in axis: pbar_style = 'Orange.Horizontal.TProgressbar'
            bar = ttk.Progressbar(row, maximum=rng, mode='determinate',
                                  length=100, style=pbar_style)
            bar.pack(side=tk.RIGHT, padx=(4, 4))

            self.pos_labels[axis]    = lbl
            self.target_labels[axis] = tgt_lbl
            self.pos_bars[axis]      = bar

        self.cart_lbl = ttk.Label(self, text="Cartesian: X = 0.0 mm, Y = 0.0 mm",
                                  font=('Consolas', 10, 'bold'), foreground=app.ACCENT)
        self.cart_lbl.pack(anchor=tk.W, pady=(4, 0))

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

class JogPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Jog Control  (WASD / Q-E / SPACE)",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 4))

        # Speed slider
        spd_row = ttk.Frame(self)
        spd_row.pack(fill=tk.X, pady=2)
        ttk.Label(spd_row, text="Speed:", width=7).pack(side=tk.LEFT)
        self.jog_speed = tk.DoubleVar(value=20.0)
        self.jog_speed_label = ttk.Label(spd_row, text="20.0", width=5,
                                         font=('Consolas', 10), foreground=app.ACCENT)
        self.jog_speed_label.pack(side=tk.RIGHT)
        ttk.Scale(spd_row, from_=0.1, to=80.0, variable=self.jog_speed,
                  orient=tk.HORIZONTAL,
                  command=lambda v: self.jog_speed_label.config(text=f"{float(v):.1f}")).pack(
                      side=tk.RIGHT, fill=tk.X, expand=True, padx=4)

        # Direction pad
        pad = ttk.Frame(self)
        pad.pack(fill=tk.X, pady=6)

        dirs = [
            ("Y+  (W)",  0, 1, (0, 1, 0)),
            ("X-  (A)",  1, 0, (-1, 0, 0)),
            ("STOP",     1, 1, (0, 0, 0)),
            ("X+  (D)",  1, 2, (1, 0, 0)),
            ("Y-  (S)",  2, 1, (0, -1, 0)),
        ]
        for text, r, c, dirs_tuple in dirs:
            if text == 'STOP':
                b = ttk.Button(pad, text=text, command=app._jog_stop, style='Danger.TButton', width=8)
                b.grid(row=r, column=c, padx=2, pady=2, sticky='nsew')
            else:
                b = ttk.Button(pad, text=text, style='TButton', width=8)
                b.grid(row=r, column=c, padx=2, pady=2, sticky='nsew')
                dx, dy, dz = dirs_tuple
                b.bind('<ButtonPress-1>', lambda event, x=dx, y=dy, z=dz: app._jog_start(x, y, z))
                b.bind('<ButtonRelease-1>', lambda event: app._jog_stop())
        for i in range(3):
            pad.columnconfigure(i, weight=1)

        # Z buttons
        z_row = ttk.Frame(self)
        z_row.pack(fill=tk.X, pady=4)
        
        bz_up = ttk.Button(z_row, text="Z+  (Q)", width=10)
        bz_up.pack(side=tk.LEFT, expand=True, padx=2)
        bz_up.bind('<ButtonPress-1>', lambda event: app._jog_start(0, 0, 1))
        bz_up.bind('<ButtonRelease-1>', lambda event: app._jog_stop())

        bz_down = ttk.Button(z_row, text="Z-  (E)", width=10)
        bz_down.pack(side=tk.LEFT, expand=True, padx=2)
        bz_down.bind('<ButtonPress-1>', lambda event: app._jog_start(0, 0, -1))
        bz_down.bind('<ButtonRelease-1>', lambda event: app._jog_stop())

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

class JointSpacePanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Target Position",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 4))

        self.target_entries = {}
        axis_cfg = [
            ('X_deg', 'X (deg):',  0,   360),
            ('Y_deg', 'Y (deg):',  0,   360),
            ('Z_mm',  'Z (mm):',   0,   100),
        ]
        for key, label, default, rng in axis_cfg:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=9).pack(side=tk.LEFT)

            entry = ttk.Entry(row, width=9, font=('Consolas', 11))
            entry.insert(0, str(default))
            entry.pack(side=tk.LEFT, padx=3)

            slider_var = tk.DoubleVar(value=default)
            slider = ttk.Scale(row, from_=-rng, to=rng, variable=slider_var,
                               orient=tk.HORIZONTAL,
                               command=lambda v, e=entry, sv=slider_var: self._sync_entry(e, sv))
            slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=3)

            self.target_entries[key] = (entry, slider, slider_var)

        ttk.Button(self, text="▶  Send Target Position",
                   command=app._send_target,
                   style='Accent.TButton').pack(fill=tk.X, pady=8)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

    def _sync_entry(self, entry, var):
        """Keep entry field in sync with slider drag."""
        entry.delete(0, tk.END)
        entry.insert(0, f"{var.get():.1f}")

class CartesianIKPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Cartesian Target (IK)",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 4))

        self.cart_entries = {}
        
        # Link lengths config row
        link_row = ttk.Frame(self)
        link_row.pack(fill=tk.X, pady=1)
        ttk.Label(link_row, text="L1 (mm):", width=9).pack(side=tk.LEFT)
        e_l1 = ttk.Entry(link_row, width=7, font=('Consolas', 10))
        e_l1.insert(0, "200.0")
        e_l1.pack(side=tk.LEFT, padx=2)
        ttk.Label(link_row, text="L2 (mm):", width=9).pack(side=tk.LEFT, padx=(10, 0))
        e_l2 = ttk.Entry(link_row, width=7, font=('Consolas', 10))
        e_l2.insert(0, "150.0")
        e_l2.pack(side=tk.LEFT, padx=2)
        self.cart_entries['L1_mm'] = (e_l1, None, None)
        self.cart_entries['L2_mm'] = (e_l2, None, None)

        # Offset config row
        offset_row = ttk.Frame(self)
        offset_row.pack(fill=tk.X, pady=1)
        ttk.Label(offset_row, text="Off1 (deg):", width=9).pack(side=tk.LEFT)
        e_off1 = ttk.Entry(offset_row, width=7, font=('Consolas', 10))
        e_off1.insert(0, "0.0")
        e_off1.pack(side=tk.LEFT, padx=2)
        ttk.Label(offset_row, text="Off2 (deg):", width=9).pack(side=tk.LEFT, padx=(10, 0))
        e_off2 = ttk.Entry(offset_row, width=7, font=('Consolas', 10))
        e_off2.insert(0, "0.0")
        e_off2.pack(side=tk.LEFT, padx=2)
        self.cart_entries['Off1_deg'] = (e_off1, None, None)
        self.cart_entries['Off2_deg'] = (e_off2, None, None)

        axis_cfg = [
            ('X_mm', 'X (mm):',   0,  350),
            ('Y_mm', 'Y (mm):',   0,  350),
            ('Z_mm', 'Z (mm):',   0,  100),
        ]
        for key, label, default, rng in axis_cfg:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=9).pack(side=tk.LEFT)

            entry = ttk.Entry(row, width=9, font=('Consolas', 11))
            entry.insert(0, str(default))
            entry.pack(side=tk.LEFT, padx=3)

            slider_var = tk.DoubleVar(value=default)
            slider = ttk.Scale(row, from_=-rng, to=rng, variable=slider_var,
                               orient=tk.HORIZONTAL,
                               command=lambda v, e=entry, sv=slider_var: self._sync_entry(e, sv))
            slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=3)

            self.cart_entries[key] = (entry, slider, slider_var)

        # Elbow configuration
        elbow_row = ttk.Frame(self)
        elbow_row.pack(fill=tk.X, pady=3)
        self.elbow_up_var = tk.IntVar(value=1)
        ttk.Radiobutton(elbow_row, text="Elbow UP", variable=self.elbow_up_var, value=1).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(elbow_row, text="Elbow DOWN", variable=self.elbow_up_var, value=0).pack(side=tk.LEFT, padx=10)

        ttk.Button(self, text="⚡  Apply Cartesian Target",
                   command=app._send_cartesian_target,
                   style='Success.TButton').pack(fill=tk.X, pady=6)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

    def _sync_entry(self, entry, var):
        """Keep entry field in sync with slider drag."""
        entry.delete(0, tk.END)
        entry.insert(0, f"{var.get():.1f}")

class ServoPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Servo Control",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 4))

        self.servo1_var = tk.DoubleVar(value=0)
        self.servo2_var = tk.DoubleVar(value=0)

        for label, var, lo, hi in [
            ("Servo 1 (-90..90):", self.servo1_var, -90, 90),
            ("Servo 2 (0..100):",  self.servo2_var,   0, 100),
        ]:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=17).pack(side=tk.LEFT)
            val_lbl = ttk.Label(row, text="0", width=5,
                                font=('Consolas', 10), foreground=app.PURPLE)
            val_lbl.pack(side=tk.RIGHT)
            ttk.Scale(row, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL,
                      command=lambda v, lbl=val_lbl: lbl.config(
                          text=f"{float(v):.0f}")).pack(
                          side=tk.RIGHT, fill=tk.X, expand=True, padx=3)

        ttk.Button(self, text="Set Servos", command=app._send_servos).pack(fill=tk.X, pady=5)
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

class MotorConfigPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Motor Speed / Accel",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 4))

        self.cfg_vars = {}
        cfg_items = [
            ('Speed X',  8000,  100, 20000),
            ('Accel X',  5000,  100, 15000),
            ('Speed Y', 12000,  100, 25000),
            ('Accel Y',  5000,  100, 15000),
            ('Speed Z',  8000,  100, 20000),
            ('Accel Z',  5000,  100, 15000),
        ]
        for name, default, lo, hi in cfg_items:
            row = ttk.Frame(self)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{name}:", width=9).pack(side=tk.LEFT)
            var = tk.DoubleVar(value=default)
            val_lbl = ttk.Label(row, text=str(default), width=7,
                                font=('Consolas', 9), foreground=app.ACCENT)
            val_lbl.pack(side=tk.RIGHT)
            ttk.Scale(row, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL,
                      command=lambda v, lbl=val_lbl: lbl.config(
                          text=f"{float(v):.0f}")).pack(
                          side=tk.RIGHT, fill=tk.X, expand=True, padx=3)
            self.cfg_vars[name] = (var, val_lbl)

        ttk.Button(self, text="Apply Motor Config",
                   command=app._send_config,
                   style='Purple.TButton').pack(fill=tk.X, pady=6)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

class ActionPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="System Commands",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 5))

        ttk.Button(self, text="🏠  Homing Sequence",
                   command=lambda: app._send_cmd('HOMING'),
                   style='Accent.TButton').pack(fill=tk.X, pady=3)
        ttk.Button(self, text="🔄  Reset",
                   command=lambda: app._send_cmd('RESET')).pack(fill=tk.X, pady=3)
        ttk.Button(self, text="⛔  EMERGENCY STOP  (Space)",
                   command=app._emergency,
                   style='Danger.TButton').pack(fill=tk.X, pady=6)

        # Homing status
        self.homing_label = ttk.Label(self, text="Homing: NONE",
                                      foreground=app.FG_DIM,
                                      font=('Segoe UI', 10))
        self.homing_label.pack(anchor=tk.W, pady=2)

        # Motor state
        self.motor_label = ttk.Label(self, text="Motors: ENABLED",
                                     foreground=app.GREEN,
                                     font=('Segoe UI', 10))
        self.motor_label.pack(anchor=tk.W, pady=1)

        # Last command
        self.lastcmd_label = ttk.Label(self, text="Last Cmd: NONE",
                                       foreground=app.FG_DIM,
                                       font=('Segoe UI', 9))
        self.lastcmd_label.pack(anchor=tk.W, pady=1)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

class LogPanel(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        ttk.Label(self, text="Activity Log",
                  style='SubHeader.TLabel').pack(anchor=tk.W, pady=(0, 3))

        self.log_text = tk.Text(self, height=8, wrap=tk.WORD,
                                bg=app.BG_LIGHT, fg=app.FG,
                                font=('Consolas', 9), relief=tk.FLAT,
                                insertbackground=app.FG, borderwidth=0,
                                highlightthickness=1, highlightcolor=app.ACCENT)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # Configure log text tags for coloring
        self.log_text.tag_config('info',    foreground=app.FG)
        self.log_text.tag_config('success', foreground=app.GREEN)
        self.log_text.tag_config('warning', foreground=app.YELLOW)
        self.log_text.tag_config('error',   foreground=app.RED)

        ttk.Button(self, text="Clear Log", command=app._clear_log).pack(fill=tk.X, pady=3)

# Decoupled AutomationLoopPanel is now imported from automation_loop.py
