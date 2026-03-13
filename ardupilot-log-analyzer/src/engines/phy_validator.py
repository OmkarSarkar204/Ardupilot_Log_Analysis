# phy_validator.py

def physics_validator(motor_spread, roll_error, volt_sag, power_watts, spread_thresh, roll_thresh, sag_thresh):
    '''Dynamic physical limits based on specific flight baselines'''
    if motor_spread > spread_thresh and roll_error > roll_thresh:
        return 1
    
    if volt_sag > sag_thresh:
        return 2
        
    return 0