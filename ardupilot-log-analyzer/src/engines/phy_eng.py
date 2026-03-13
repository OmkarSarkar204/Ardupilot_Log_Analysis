import pandas as pd

def calculate_mechanical_features(df):
    """Calculates attitude and motor imbalance features."""
    if "roll" in df.columns and "des_roll" in df.columns:
        df["roll_error"] = (df["des_roll"] - df["roll"]).abs()
    return df

def calculate_power_features(df):
    """Calculates battery health and voltage sag features."""
    if "Volt" in df.columns:
        max_v = df["Volt"].max()
        df["volt_sag"] = max_v - df["Volt"]

    if "Volt" in df.columns and "Curr" in df.columns:
        df["power_watts"] = df["Volt"] * df["Curr"]
    return df

def process_physics(data, label=None, ground_pwm_limit=1200):
    att_signals = data["signals"].get("ATT", [])
    rcou_signals = data["signals"].get("RCOU", [])
    bat_signals = data["signals"].get("BAT", [])
    motor_channels = data["motor_channels"]

    if not att_signals or not rcou_signals:
        return pd.DataFrame()

    # Rebuild ATT
    att_df = pd.DataFrame(att_signals)
    att_df = att_df.rename(columns={
        "TimeUS": "time", 
        "Roll": "roll", 
        "DesRoll": "des_roll"
    })
    req_att_cols = [c for c in ["time", "roll", "des_roll"] if c in att_df.columns]
    att_df = att_df.dropna(subset=req_att_cols).sort_values("time")

    # Rebuild BAT
    if bat_signals:
        bat_df = pd.DataFrame(bat_signals)
        bat_df = bat_df.rename(columns={"TimeUS": "time"})
        if "time" in bat_df.columns:
            bat_df = bat_df.dropna(subset=["time"]).sort_values("time")
    else:
        bat_df = pd.DataFrame(columns=["time"])

    # Rebuild RCOU
    rows = []
    for rcou in rcou_signals:
        time = rcou.get("time_us")
        outputs = rcou.get("outputs", {})
        motors = []
        
        for ch in motor_channels:
            key = f"C{ch}"
            if key in outputs:
                motors.append(outputs[key])

        if len(motors) != len(motor_channels) or not motors:
            continue

        rows.append({
            "time": time,
            "motor_spread": max(motors) - min(motors),
            "max_pwm": max(motors)
        })

    if not rows:
        return pd.DataFrame()

    rcou_df = pd.DataFrame(rows).sort_values("time")

    # Align Timelines
    df = pd.merge_asof(rcou_df, att_df, on="time", direction="nearest")
    
    if not bat_df.empty:
        df = pd.merge_asof(df, bat_df, on="time", direction="nearest")

    # Run Physics Modules
    df = calculate_mechanical_features(df)
    df = calculate_power_features(df)

    # Filter Ground Data
    df = df[df["max_pwm"] > ground_pwm_limit]
    
    if df.empty:
        return pd.DataFrame()

    df["time_sec"] = df["time"] / 1_000_000
    if label is not None:
      df["label"] = label

    # Select final columns safely
    desired_cols = ["time_sec", "motor_spread", "roll_error", "volt_sag", "power_watts", "label"]
    final_cols = [c for c in desired_cols if c in df.columns]

    return df[final_cols]