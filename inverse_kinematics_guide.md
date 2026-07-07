# SCARA Robot: Inverse Kinematics (IK) & Trajectory Walkthrough

This educational guide provides a step-by-step breakdown of how the SCARA robot converts desired $(X, Y, Z)$ spatial coordinates into physical joint rotations and stepper motor pulses.

---

## 1. The Core Geometric Logic (2D Plane)

A SCARA (Selective Compliance Assembly Robot Arm) operates primarily in a 2D horizontal plane ($X-Y$) using two rotating links:
- **Link 1 ($L_1$)**: The shoulder arm, rotatable by angle $\theta_1$ relative to the base X-axis.
- **Link 2 ($L_2$)**: The elbow arm, rotatable by angle $\theta_2$ relative to Link 1.

```
              Elbow (x1, y1)
                o - - - - - - - o End-Effector (X, Y)
               / \    L2
              /   \
          L1 /     \
            /       \
           / theta1  \
   Base   o - - - - - - - - - - X-axis
```

To find the joint angles $(\theta_1, \theta_2)$ required to reach a target coordinate $(X, Y)$, we use trigonometry.

### Step A: Radial Distance & Boundary Validation
We compute the distance $R$ from the base origin $(0, 0)$ to the target $(X, Y)$:
$$R = \sqrt{X^2 + Y^2}$$

Before running any math, we validate boundaries to protect the robot:
1. **Outer Boundary**: The target is too far ($R > L_1 + L_2$). The arm cannot stretch this far.
2. **Inner Boundary**: The target is too close ($R < |L_1 - L_2|$). The arm cannot fold back enough.

If either condition is met, the solver cancels execution to prevent mechanical stress.

### Step B: Solving for Elbow Angle ($\theta_2$)
Using the **Law of Cosines** on the triangle formed by $L_1$, $L_2$, and $R$:
$$R^2 = L_1^2 + L_2^2 - 2 L_1 L_2 \cos(180^\circ - \theta_2)$$

Since $\cos(180^\circ - \theta_2) = -\cos(\theta_2)$, we simplify:
$$R^2 = L_1^2 + L_2^2 + 2 L_1 L_2 \cos(\theta_2)$$

Solving for $\cos(\theta_2)$:
$$\cos(\theta_2) = \frac{X^2 + Y^2 - L_1^2 - L_2^2}{2 L_1 L_2}$$

We clamp $\cos(\theta_2)$ to $[-1.0, 1.0]$ to prevent numerical errors, and solve:
$$\theta_2 = \arccos(\cos(\theta_2))$$

### Step C: Solving for Shoulder Angle ($\theta_1$)
Once $\theta_2$ is known, we find $\theta_1$. Let $\alpha$ be the angle of the target vector relative to the base X-axis, and $\beta$ be the internal angle between $L_1$ and the target vector:
$$\theta_1 = \alpha - \beta$$
$$\alpha = \text{atan2}(Y, X)$$
$$\beta = \text{atan2}(L_2 \sin(\theta_2), L_1 + L_2 \cos(\theta_2))$$

Thus:
$$\theta_1 = \text{atan2}(Y, X) - \text{atan2}(L_2 \sin(\theta_2), L_1 + L_2 \cos(\theta_2))$$

---

## 2. The Elbow UP vs DOWN Posture Mechanism

Because the triangle can be flipped across the target vector line, there are always **two geometric solutions** for any reachable $(X, Y)$ coordinate:

1. **Elbow UP ($\theta_2 > 0$)**: The elbow bends upwards.
2. **Elbow DOWN ($\theta_2 < 0$)**: The elbow bends downwards.

```
       Elbow UP                     Elbow DOWN
          o                            Base
         / \                          /   \
  Base  o   o Target         Target  o     o Elbow
```

### Why it was failing & How it was fixed:
- **The Issue**: In Tkinter, using raw python booleans (`True`/`False`) inside `ttk.Radiobutton` can fail or default because Tcl interprets them as strings `"True"`/`"False"`, preventing dynamic toggle updates.
- **The Fix**: We updated the selector variable to a standard `tk.IntVar` with explicit integer values (`1` for UP, `0` for DOWN). This configuration is cast to a boolean on submission and correctly changes the sign of $\theta_2$ before solving for $\theta_1$:
  $$\theta_2 = \begin{cases} \arccos(\cos(\theta_2)) & \text{if Elbow UP} \\ -\arccos(\cos(\theta_2)) & \text{if Elbow DOWN} \end{cases}$$
- **Angle Wrapping**: The raw difference of two `atan2` angles in $\theta_1$ can lie outside $[-\pi, \pi]$ (e.g. $-190^\circ$). If not wrapped, sending the target would cause the motor to take a long $350^\circ$ path instead of a $10^\circ$ shortcut. Wrapping angles ensures perfect determinism and repeatability:
  $$\theta = (\theta + \pi) \pmod{2\pi} - \pi$$

---

## 3. Conversion to Discrete Motion

Once the target joint angles ($\theta_1, \theta_2$) are solved, they are transmitted to the ESP32.

### Step A: Angle-to-Step Conversion
Continuous joint angles in degrees are converted to discrete stepper motor steps using physical constants:
$$\text{Steps} = \text{Angle} \times \left( \frac{\text{Steps per Revolution} \times \text{Microstepping} \times \text{Gear Ratio}}{360^\circ} \right)$$
In our firmware, these mapping coefficients are pre-calculated:
- **Joint 1 (X)**: $47.058 \text{ steps/degree}$
- **Joint 2 (Y)**: $585.830 \text{ steps/degree}$
- **Axis 3 (Z)**: $10.000 \text{ steps/mm}$

To prevent truncation jitter (where values like `4999.99` truncate to `4999`), we use `lround()` to round to the nearest whole step.

### Step B: Synchronized Trajectory Generator
If one joint needs to travel $180^\circ$ and another only $10^\circ$, driving both at their maximum speeds would cause the second joint to finish immediately while the first is still moving, causing the hand to curve widely.
To maintain a straight coordinate trace:
1. We calculate travel distances: $\Delta_X, \Delta_Y, \Delta_Z$.
2. We compute the transit time at full speed for each axis: $T_i = \frac{\Delta_i}{V_{max, i}}$.
3. We select the maximum time $T_{max} = \max(T_X, T_Y, T_Z)$.
4. We scale the speeds and accelerations of the other axes:
   $$V_{run, i} = \frac{\Delta_i}{T_{max}}$$
   $$A_{run, i} = A_{limit, i} \times \left( \frac{V_{run, i}}{V_{max, i}} \right)$$

This guarantees all axes accelerate, coast, and decelerate proportionally, reaching the target simultaneously.

### Step C: S-Curve Jerk Filtering
Jogging and differential inputs (streamed in 30ms packets) are routed through a Jerk-Limited S-curve acceleration filter in the firmware loop. The velocity ramps smoothly at each step to prevent mechanical vibration and slippage:
$$\text{Jerk} = \frac{\Delta \text{Acceleration}}{\Delta t}$$
$$\text{Acceleration} = \text{Acceleration} + \text{Jerk} \times dt$$
$$\text{Velocity} = \text{Velocity} + \text{Acceleration} \times dt$$
This ensures the physical motors transition smoothly between stop and high-speed motion states.
