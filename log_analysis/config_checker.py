from log_analysis.parser.bin_parser import BinParser

parser = BinParser(
    "flight.bin"
)

parsed = parser.parse()

print(parsed.firmware)

print(parsed.params["INS_GYRO_FILTER"])

print(parsed.metadata["INS_GYRO_FILTER"])

print(len(parsed.vibe))