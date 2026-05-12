from pathlib import Path

from pymavlink import mavutil

from ardupilot_methodic_configurator.annotate_params import (
    PARAM_DEFINITION_XML_FILE,
    get_fallback_xml_url,
    get_xml_url,
    parse_parameter_metadata,
)
from ardupilot_methodic_configurator.extract_param_defaults import (
    extract_firmware_version_and_vehicle_type,
    extract_parameter_values,
)


class ParsedLog:
    def __init__(self):
        self.params = {}
        self.vibe = []
        self.esc = []
        self.rcou = []
        self.imu = []
        self.firmware = {}
        self.metadata = {}


class BinParser:
    def __init__(self, logfile):
        self.logfile = logfile

    def load_metadata(self, vehicle, version):
        xml_dir = str(Path(self.logfile).parent)
        xml_url = get_xml_url(vehicle, version)
        fallback_url = get_fallback_xml_url(vehicle, version)
        metadata = parse_parameter_metadata(
            xml_url=xml_url,
            xml_dir=xml_dir,
            xml_file=PARAM_DEFINITION_XML_FILE,
            vehicle_type=vehicle,
            max_line_length=120,
            fallback_xml_url=fallback_url,
        )

        return metadata

    def parse(self):

        parsed = ParsedLog()
        parsed.params = extract_parameter_values(self.logfile, "values")
        vehicle, major, minor, patch = extract_firmware_version_and_vehicle_type(self.logfile)

        version = f"{major}.{minor}.{patch}"

        parsed.firmware = {
            "vehicle": vehicle,
            "version": version,
        }

        # PARAMETER METADATA
        parsed.metadata = self.load_metadata(vehicle, version)

        # LOG PARSING
        mlog = mavutil.mavlink_connection(self.logfile)

        while True:
            msg = mlog.recv_match(blocking=False)

            if msg is None:
                break

            mtype = msg.get_type()

            if mtype == "ESC":
                parsed.esc.append(
                    {
                        "time": getattr(msg, "TimeUS", None),
                        "rpm": getattr(msg, "RPM", None),
                    }
                )


parser = BinParser("log_analysis/2026-04-07 18-39-06.bin")

parsed = parser.parse()

print(parsed.firmware)

print(parsed.params["INS_GYRO_FILTER"])

print(parsed.metadata["INS_GYRO_FILTER"])

print(len(parsed.vibe))
