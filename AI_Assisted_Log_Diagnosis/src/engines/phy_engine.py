import pandas as pd


# mechanical / attitude related features
def calculate_mechanical_features(df):

    # roll tracking error
    if "roll" in df.columns and "des_roll" in df.columns:
        df["roll_error"] = (df["des_roll"] - df["roll"]).abs()

    # change in roll error (can show instability growing)
    if "roll_error" in df.columns:
        df["roll_rate"] = df["roll_error"].diff().fillna(0)
    return df



# battery + power related features
def calculate_power_features(df):

    # voltage sag relative to max seen in log
    if "Volt" in df.columns:
        df["volt_sag"] = df["Volt"].max() - df["Volt"]

    if "Volt" in df.columns and "Curr" in df.columns:
        df["power_watts"] = df["Volt"] * df["Curr"]

    # rate of power change
    if "power_watts" in df.columns:
        df["power_delta"] = df["power_watts"].diff().fillna(0)

    # debug maybe check spikes here
    # print("power features")

    return df



# rolling / time window features (mostly for ML)
def calculate_time_features(df):

    if "motor_spread" in df.columns:
        df["spread_mean_3s"] = df["motor_spread"].rolling(window=30, min_periods=1).mean()

    if "volt_sag" in df.columns:
        df["sag_max_3s"] = df["volt_sag"].rolling(window=30, min_periods=1).max()
        df["sag_slope"] = df["volt_sag"].diff(periods=10)

    cols_to_clean = ["spread_mean_3s", "sag_max_3s", "sag_slope"]

    for col in cols_to_clean:

        if col in df.columns:
            df[col] = df[col].fillna(0)

    # maybe move these window sizes to config later
    return df



# convert raw signals to zscore anomaly scale
def apply_fdir_statistics(df):

    # baseline window ~5% of log
    window_size = max(10, int(len(df) * 0.05))

    features_to_score = [
        "motor_spread",
        "roll_error",
        "volt_sag",
        "power_delta",
    ]

    for col in features_to_score:

        if col in df.columns:

            baseline_mean = df[col].head(window_size).mean()
            baseline_std = df[col].head(window_size).std()

            # avoid divide by zero
            if baseline_std == 0 or pd.isna(baseline_std):
                baseline_std = 1e-6

            df[f"{col}_zscore"] = (df[col] - baseline_mean) / baseline_std


    # correlation between motor load + battery voltage
    if "motor_spread" in df.columns and "Volt" in df.columns:

        df["corr_motor_volt"] = (
            df["motor_spread"]
            .rolling(window=50, min_periods=1)
            .corr(df["Volt"])
            .fillna(0)
        )

    # debug check
    return df




# main physics processing entry
def process_physics(raw_data, label=None):

    att_signals = raw_data["signals"].get("ATT", [])
    bat_signals = raw_data["signals"].get("BAT", [])
    rcou_signals = raw_data["signals"].get("RCOU", [])

    motor_channels = raw_data.get("motor_channels", [])

    if not att_signals or not rcou_signals:
        return pd.DataFrame()


    # rebuild ATT dataframe
    att_df = pd.DataFrame(att_signals)

    att_df = att_df.rename(
        columns={
            "TimeUS": "time",
            "DesRoll": "des_roll",
            "Roll": "roll",
        }
    )

    att_df = att_df.dropna(subset=["time", "des_roll", "roll"]).sort_values("time")


    # rebuild battery dataframe
    if bat_signals:

        bat_df = pd.DataFrame(bat_signals)
        bat_df = bat_df.rename(columns={"TimeUS": "time"})

        bat_df = bat_df.dropna(subset=["time"]).sort_values("time")

    else:

        bat_df = pd.DataFrame(columns=["time"])


    # rebuild motor outputs
    rows = []

    for rcou in rcou_signals:

        time = rcou.get("time_us")
        outputs = rcou.get("outputs", {})

        motors = [outputs[f"C{ch}"] for ch in motor_channels if f"C{ch}" in outputs]

        if len(motors) == len(motor_channels) and motors:

            rows.append(
                {
                    "time": time,
                    "motor_spread": max(motors) - min(motors),
                    "max_pwm": max(motors),
                }
            )


    if not rows:
        return pd.DataFrame()


    rcou_df = pd.DataFrame(rows).sort_values("time")

    # align timelines
    df = pd.merge_asof(rcou_df, att_df, on="time", direction="nearest")

    if not bat_df.empty:
        df = pd.merge_asof(df, bat_df, on="time", direction="nearest")


    # feature engineering
    df = calculate_mechanical_features(df)
    df = calculate_power_features(df)
    df = calculate_time_features(df)


    # remove ground idle
    df = df[df["max_pwm"] > 1100].copy()

    if df.empty:
        return df


    # convert time to seconds relative start
    df["time_sec"] = (df["time"] - df["time"].iloc[0]) / 1e6


    # add statistical anomaly features
    df = apply_fdir_statistics(df)


    if label is not None:
        df["label"] = label


    # TODO check oscillation log 00000082 later
    return df