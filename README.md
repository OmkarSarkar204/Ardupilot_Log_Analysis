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
