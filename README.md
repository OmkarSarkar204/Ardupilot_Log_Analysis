# ArduPilot Log Failure Diagnosis Prototype (V-3)

This prototype reads ArduPilot `.BIN` flight logs and tries to identify possible causes of failures. Right now it mainly focuses on two cases: `motor failure` and `battery issues`.

## Current Capabilities

* Parse ArduPilot `.BIN` logs using `pymavlink`
* Extract telemetry signals (`ATT`, `BAT`, `RCOU`)
* Compute mechanical and power features
* Detect anomalies in flight behavior
* Train a RandomForest classifier from labeled logs
* Identify potential root causes (motor or battery failure)
* Generate a timeline of detected anomalies

## Architecture

The analysis pipeline consists of the following stages:

### Log Parsing
The parser reads `.BIN` logs and extracts telemetry messages (`ATT`, `BAT`, `RCOU`). It dynamically identifies which servo channels correspond to motors, since different users have different channel mappings (like 33–40).
(https://ardupilot.org/copter/docs/common-rcoutput-mapping.html#default-values)

### Physics Engine
ArduPilot logs contain asynchronous telemetry streams (`ATT` ~50Hz, `RCOU` ~50Hz, `BATT` ~10Hz). The physics engine synchronizes these into a single dataframe representing the entire flight timeline. 

From this timeline a few simple physical features are computed to describe how the vehicle is behaving.
* **Motor Spread:** `max(motor_pwm) - min(motor_pwm)` (A large spread indicates motors compensating for thrust loss).
* **Roll Error:** `|desired_roll − actual_roll|` (Large errors indicate the controller is failing to stabilize).
* **Voltage Sag:** `V_max − V_current` (Indicates battery collapse or excessive current draw).

### ML Model
A RandomForest classifier is trained on a small dataset (~15 logs) generated in SITL. of `Healthy`, `Motor Issue`, and `Battery Issue` flight logs generated using ArduCopter's SITL. 


![Training Screenshot](https://github.com/OmkarSarkar204/Ardupilot_Log_Analysis/blob/main/Prototype-v1/img/Screenshot%202026-03-12%20at%204.51.03%E2%80%AFPM.png)

![Training Screenshot](https://github.com/OmkarSarkar204/Ardupilot_Log_Analysis/blob/main/Prototype-v1/img/Screenshot%202026-03-12%20at%206.28.18%E2%80%AFPM.png)


Input features include `motor_spread`, `roll_error`, `volt_sag`, `power_watts`.

### Physics Validation
The validator performs independent rule-based checks using statistics calculated dynamically from the flight's baseline. This acts like a "check engine" light to confirm whether an ML-detected anomaly is physically plausible. If both the ML model and the physics checks flag the same anomaly, the result is treated as more reliable.

### Event Detection & Diagnosis
Consecutive anomalies are grouped into continuous time windows rather than separate events. Short spikes are filtered out. The engine compares these timelines to output a final root cause (e.g., if battery voltage collapses, then motor thrust reduces and attitude becomes unstable).

## Example Output

```
running log data/raw_logs/motor_fail.BIN

FLIGHT LOG ANALYSIS REPORT
Flight Timeline
24.0s --> 27.6s PHY motor_spread dur 3.6
24.1s --> 39.0s PHY roll_error dur 14.9
65.2s --> 69.3s PHY motor_spread dur 4.1
65.2s --> 83.5s PHY roll_error dur 18.3
113.8s --> 117.9s PHY motor_spread dur 4.1
113.9s --> 155.7s PHY roll_error dur 41.8
127.8s --> 155.7s PHY motor_spread dur 27.9
128.0s --> 155.7s ML ml_motor_anomaly dur 27.7
145.3s --> 145.8s PHY power_delta dur 0.5
151.5s --> 152.0s PHY power_delta dur 0.5
ROOT CAUSE: MOTOR FAILURE
```

## Limitations and Roadmap

* Dynamic thresholds assume the early part of the flight represents healthy behaviour.  
If a vehicle already has a fault when it takes off, the baseline estimation can be wrong and the thresholds may become inaccurate.

* The current model evaluates rows independently. Because of that it misses temporal patterns like oscillations, vibrations, or slow degradation trends over time.

* Right now the model is very naive since it was trained mostly on clean SITL simulator logs.  
If I benchmark it today the accuracy numbers would probably look very high, but I wouldn't really trust them.

So the plan is to build a proper validation dataset using real crash logs from the ArduPilot forums and also logs collected from my college's drone club. If it works perfectly on the copter it should work perfectly with other vehicles too.  
Most of these logs are not labeled, so I will have to manually inspect them in Mission Planner and figure out the real cause before using them for evaluation.

The idea is to track things like correct and wrong diagnoses over time and see if the system actually improves as more data is added.

* The current prototype only looks at a few derived signals.  
Future versions should also include signals such as:

* VIBE logs (vibration)
* GPS consistency metrics
* IMU clipping detection
* ESC telemetry

These should help handle the edge cases.

### Multi-Vehicle Support

Different vehicle types need different failure logic.  
Future versions will read the `FRAME_CLASS` parameter and apply vehicle specific diagnostics.

For example:

Planes  
* engine failure may result in glide behaviour

Rovers  
* motor imbalance may produce steering drift

## Installation

```
git clone https://github.com/OmkarSarkar204/Ardupilot_Log_Analysis.git
cd Version-3
pip install -r requirements.txt
python -m main filename.BIN
```

## Version 1

A simple physics based anomaly detection engine.
* parsed logs with hardcoded motor pins (C1-C4)
* worked on SITL logs but crashed on some real user logs

## Version 2

Hybrid system combining physics checks and a machine learning classifier.
* added dataset builder
* added RandomForest classifier
* added battery failure detection

## Version 3

Event based system.
* structured anomaly timelines
* dynamic servo parsing
* separated detection and diagnosis stages
