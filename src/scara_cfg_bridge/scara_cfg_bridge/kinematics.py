import math

def calculate_inverse_kinematics(x, y, L1, L2, elbow_up=True):
    """
    Solves IK analytically.
    Returns (theta1_deg, theta2_deg) or raises ValueError if unreachable.
    """
    d_sq = x**2 + y**2
    d = math.sqrt(d_sq)
    
    max_reach = L1 + L2
    min_reach = abs(L1 - L2)
    
    if d > max_reach:
        raise ValueError(f"Target ({x:.1f}, {y:.1f}) is out of reach!\nDistance: {d:.1f} mm > Max: {max_reach:.1f} mm")
    if d < min_reach:
        raise ValueError(f"Target ({x:.1f}, {y:.1f}) inside minimum radius!\nDistance: {d:.1f} mm < Min: {min_reach:.1f} mm")
        
    cos_theta2 = (d_sq - L1**2 - L2**2) / (2.0 * L1 * L2)
    cos_theta2 = max(-1.0, min(1.0, cos_theta2))
    
    theta2 = math.acos(cos_theta2)
    if not elbow_up:
        theta2 = -theta2
        
    theta1 = math.atan2(y, x) - math.atan2(L2 * math.sin(theta2), L1 + L2 * math.cos(theta2))
    
    # Wrap angles to [-pi, pi] to prevent joint target jumping and ensure repeatable paths
    theta1 = (theta1 + math.pi) % (2.0 * math.pi) - math.pi
    theta2 = (theta2 + math.pi) % (2.0 * math.pi) - math.pi
    
    return math.degrees(theta1), math.degrees(theta2)

def calculate_forward_kinematics(theta1_deg, theta2_deg, L1, L2):
    """
    Computes Cartesian coordinates (x, y) from joint angles.
    """
    th1 = math.radians(theta1_deg)
    th2 = math.radians(theta2_deg)
    x = L1 * math.cos(th1) + L2 * math.cos(th1 + th2)
    y = L1 * math.sin(th1) + L2 * math.sin(th1 + th2)
    return x, y
