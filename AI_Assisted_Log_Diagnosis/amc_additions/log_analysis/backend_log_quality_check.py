from dataclasses import dataclass, field
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData

@dataclass
class LogQuality:
    """Quality assessment of a single ArduPilot .bin log file."""

    missing: list[str] = field(default_factory=list)

    vehicle_type: str | None = None
    firmware_version: tuple[int, int, int] | None = None
    frame_type: int | None = None
    flight_duration_s: float | None = None

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
    retchk = LogQuality()
    vehicle_type = None
    firmware_version = None
    if log_data.firmware_info is not None:
        retchk.vehicle_type = log_data.firmware_info[0]
        retchk.firmware_version = log_data.firmware_info[1:]

    frame_type = int(log_data.frame_type) if log_data.frame_type is not None else None

    # Flight duration from PM timestamps. 1e6 converts microsecond to second
    if len(log_data.performance_monitor.time_us) >= 2:
        retchk.flight_duration_s = (log_data.performance_monitor.time_us[-1] - log_data.performance_monitor.time_us[0]) / 1e6
    else:
        retchk.flight_duration_s = None

    retchk.has_params = len(log_data.default_params) > 0
    retchk.has_battery = len(log_data.batteries) > 0
    retchk.has_imu = len(log_data.imu_data) > 0
    retchk.has_vibe = len(log_data.vibe_data) > 0
    retchk.has_gps = len(log_data.gps_data) > 0
    retchk.has_pm = len(log_data.performance_monitor.time_us) > 0
    retchk.has_att = "ATT" in log_data.messages
    retchk.has_rate = "RATE" in log_data.messages
    retchk.has_rcou = "RCOU" in log_data.messages
    retchk.has_esc = "ESC" in log_data.messages
    retchk.has_ekf = "XKF1" in log_data.messages
    retchk.has_fft = "ISBH" in log_data.messages and "ISBD" in log_data.messages


    presence_checks = {
      "Parameters": retchk.has_params,
      "Battery": retchk.has_battery,
      "IMU": retchk.has_imu,
      "Vibration": retchk.has_vibe,
      "GPS": retchk.has_gps,
      "Processor Load": retchk.has_pm,
      "ATT": retchk.has_att,
      "RATE": retchk.has_rate,
      "Motor Outputs": retchk.has_rcou,
      "ESC Telemetry": retchk.has_esc,
      "EKF": retchk.has_ekf,
      "FFT": retchk.has_fft,
    }

    retchk.missing = [checks for checks, present in presence_checks.items() if not present]

