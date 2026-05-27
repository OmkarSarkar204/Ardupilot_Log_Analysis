# ArduPilot Log Diagnosis

Automated analysis of ArduPilot flight logs to identify what happened, when it happened, and why.

This project builds a structured pipeline for analyzing `.BIN` logs using deterministic signal processing and model-based validation.

## Status

This repository contains active development work.  
The current implementation is under `AI_Assisted_Log_Diagnosis/`, while earlier iterations are preserved in `old_versions/`.  

## Problem

ArduPilot logs contain high-frequency telemetry from multiple subsystems, recorded at different rates and without a unified time base.  
Understanding failures requires correlating attitude, motor outputs, vibration, power systems, and estimator behavior across time.

In practice, this is still done manually. It is slow, error-prone, and heavily dependent on experience.

## Approach

The system is designed as a sequential pipeline.

It begins with log ingestion, where `.BIN` files are parsed through MAVLink and relevant message types are extracted and normalized.  
Since signals are recorded asynchronously, the next step aligns them into a consistent time representation.

Once aligned, raw telemetry is transformed into structured signal groups such as motor behavior, IMU dynamics, battery response, and estimator state. These representations are then evaluated using physics-based checks derived from expected flight behavior.

Instead of reacting to short-lived spikes, the system focuses on sustained deviations. A temporal layer is then applied to validate patterns over time and suppress noise.

Finally, all detections are combined into a structured diagnosis that links each conclusion directly to the underlying telemetry.

## Design Principles To Achieve

The system will be built around deterministic and traceable logic. Every output must be explainable through actual signals rather than heuristics.  
The architecture is modular so that new vehicle types and analysis modules can be added without restructuring the pipeline.

## Current Scope

The current focus is on Copter logs.  
Work so far includes ingestion, motor-related signal extraction, and IMU/vibration handling.

The same structure is intended to support Plane, Rover, and Sub once the base pipeline stabilizes.

``` mermaid
flowchart TB
 subgraph Input["INPUT"]
        A[".BIN Flight Log"]
        B["PyMavlink Parser"]
        C["Raw MAVLink Signals"]
  end
 subgraph Processing["SIGNAL PROCESSING"]
        D["Time Alignment"]
        E["Resampling"]
        F[("Structured Data")]
  end
 subgraph Features["FEATURE EXTRACTION"]
        G1["Battery Features"]
        G2["IMU Features"]
        G3["Motor Features"]
        G4["Control Features<br>Attitude &amp; Rate Error"]
        G5["Estimator Features<br>EKF Consistency"]
  end
 subgraph Parallel["PARALLEL ANALYSIS"]
        P1["Physics Engine<br>Limits &amp; Patterns"]
        P2["ML Layer<br>HMM State Detection"]
  end
 subgraph Fusion["COMBINATION"]
        H["Combine Physics + ML Outputs"]
  end
 subgraph Causal["CAUSE ANALYSIS"]
        I["Event Linking<br>Time ordered Dependencies"]
        J["Root Cause Identification"]
  end
 subgraph ParamCheck["PARAMETER VALIDATION"]
        X["Parameters"]
        Y["Range & Conflict Checks"]
  end
 subgraph AMC["AMC CONFIGURATION LAYER"]
        K["Map to AMC Tuning Step"]
        L{"Config Issue?"}
        M["Suggest Parameter Changes"]
  end
 subgraph Loop["USER LOOP"]
        O["User Review"]
        P["Apply via MAVLink"]
        Q["Retest Flight"]
        R["Compare Logs"]
  end
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G1 & G2 & G3 & G4 & G5
    G1 --> P1
    G2 --> P1
    G4 --> P2
    G5 --> P2
    P1 --> H
    P2 --> H
    H --> I
    I --> J
    J --> X & L
    X --> Y
    Y --> L
    L -- No --> O
    L -- Yes --> K
    K --> M
    M --> O
    O --> P
    P --> Q
    Q --> R
    R --> A
    G3 --> P1
    G3 --> P2
```
