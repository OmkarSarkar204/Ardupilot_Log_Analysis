A purely physics-based anomaly detection engine for ArduPilot DataFlash (.BIN) logs. Built to prove hardware failures (e.g., motor desync, thrust loss).

**Asynchronous Data Handling**: Successfully mapped disparate telemetry streams (`ATT` at 50Hz, `BAT` at 10Hz, `RCOU` at 50Hz, `VIBE` at 100Hz) into independent time-indexed dictionaries to prevent index misalignment.

**Dynamic Hardware Profiling**: Eliminated "magic numbers" by dynamically extracting `PARM` headers (e.g., `SERVO1_MAX` to `SERVO4_MAX`) at runtime. The engine automatically adapts its mathematical saturation limits to the specific vehicle's hardware configuration.

**Motor Imbalance detection**: Sustained Motor Spread > 300Maximum PWM > 95% of dynamically detected ceilingCondition maintained for $N$ consecutive samples to filter out wind-correction noise

**Real Log validation**: Successfully parsed a wild ArduCopter forum log (mo_111 crash), bypassing software noise (EKF/Compass errors) to mathematically pinpoint the exact timestamp (269.47 s) of hardware failure.

### Where development stopped

This version only implements:

- log parsing
- basic physics checks
- single anomaly type (motor imbalance)

Next version will restructure the pipeline and add multiple subsystem analyzers (propulsion + power) along with ML based classification.