from dataclasses import dataclass, field
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData, extract_log


@dataclass
class LogQuality:
    """Quality assessment of a single ArduPilot .bin log file."""

    missing: list[str] = field(default_factory=list)

    vehicle_type: str | None
    firmware_version: tuple[int, int, int] | None
    frame_type: int | None
    flight_duration_s: float | None

    has_params: bool
    has_battery: bool
    has_imu: bool
    has_vibe: bool
    has_gps: bool
    has_pm: bool
    has_att: bool
    has_rate: bool
    has_rcou: bool
    has_ekf: bool
    has_esc: bool
    has_fft: bool



def check_log_quality(log_data: LogData) -> LogQuality:
    """
    Assess the quality of an ArduPilot .bin log for analysis suitability.

    Args:
        log_data: A populated LogData object from extract_log().

    Returns:
        A LogQuality object of what data is present and what
        analysis is possible.

    """
    vehicle_type = None
    firmware_version = None
    if log_data.firmware_info is not None:
        vehicle_type = log_data.firmware_info[0]
        firmware_version = log_data.firmware_info[1:]

    frame_type = int(log_data.frame_type) if log_data.frame_type is not None else None

    # Flight duration from PM timestamps. 1e6 converts microsecond to second
    if len(log_data.performance_monitor.time_us) >= 2:
        flight_duration_s = (log_data.performance_monitor.time_us[-1] - log_data.performance_monitor.time_us[0]) / 1e6
    else:
        flight_duration_s = None

    has_params = len(log_data.default_params) > 0
    has_battery = len(log_data.batteries) > 0
    has_imu = len(log_data.imu_data) > 0
    has_vibe = len(log_data.vibe_data) > 0
    has_gps = len(log_data.gps_data) > 0
    has_pm = len(log_data.performance_monitor.time_us) > 0
    has_att = "ATT" in log_data.messages
    has_rate = "RATE" in log_data.messages
    has_rcou = "RCOU" in log_data.messages
    has_esc = "ESC" in log_data.messages
    has_ekf = "XKF1" in log_data.messages
    has_fft = "ISBH" in log_data.messages and "ISBD" in log_data.messages

    presence_checks = {
        "Params": has_params,
        "BAT":    has_battery,
        "IMU":        has_imu,
        "VIBE":  has_vibe,
        "GPS":        has_gps,
        "PM": has_pm,
        "ATT":        has_att,
        "RATE":       has_rate,
        "RCOU": has_rcou,
        "ESC": has_esc,
        "EKF":        has_ekf,
        "FFT": has_fft,
    }

    missing = [item_present for item_present, present in presence_checks.items() if not present]

    return LogQuality(
        vehicle_type=vehicle_type,
        firmware_version=firmware_version,
        frame_type=frame_type,
        flight_duration_s=flight_duration_s,
        has_params=has_params,
        has_battery=has_battery,
        has_imu=has_imu,
        has_vibe=has_vibe,
        has_gps=has_gps,
        has_pm=has_pm,
        has_att=has_att,
        has_rate=has_rate,
        has_rcou=has_rcou,
        has_ekf=has_ekf,
        has_esc=has_esc,
        has_fft=has_fft,
        missing=missing,
    )

