## Prototype For GSoC 2026 - ArduPilot

Note: This is not the final repo for this project all developement work and testing will take place here along with the final prototype, before starting the official project this repo will stay active.

The current working model is in old_versions/Version3

Current developing folder `AI_Assisted_Log_Diagnosis`

Another NOTE: The Version-3 in the main repo contains only a readme for the Proposal



# AI-Assisted Log Diagnosis for ArduPilot

## Overview

This project aims to simplify ArduPilot log analysis by automatically explaining **why a crash or unexpected behavior occurred**.

Currently, users must manually inspect `.BIN` flight logs and interpret patterns across multiple signals. This process is complex, time-consuming, and heavily dependent on expert knowledge.

This tool automates that process by analyzing telemetry data and identifying **cause-and-effect relationships over time**.



## How It Works

The system processes a flight log through the following pipeline:

1. **Log Parsing & Time Alignment**
   - Handles asynchronous sensor data recorded at different rates
   - Aligns signals into consistent time windows

2. **Feature Generation**
   - Extracts and computes relevant metrics from telemetry

3. **Dual-Layer Analysis**
   - **Physics-based checks** → detect violations of expected flight behavior  
   - **ML model (Hidden Markov Model)** → validate patterns over time

4. **Aggregation**
   - Combines results from both layers
   - Filters noise and ensures only sustained anomalies are considered

5. **Final Diagnosis**
   - Produces a structured explanation of the root cause



## Core Approach

- Combine **deterministic physics rules** with a **sequence-based ML model (HMM)**
- Accept detections only when both agree over sustained time
- Filter noise by evaluating consistency instead of reacting to spikes

This avoids relying purely on rules or ML, both of which are unreliable on noisy real-world logs.


## Role of LLM

An **LLM-based agent** is used only for:
- Coordinating tool execution
- Combining outputs into clear explanations

All computations remain deterministic and traceable.


## Key Features

- Explains **what happened, when it happened, and why**
- Links every conclusion to actual telemetry data
- Suggests possible fixes
- Adapts to different firmware versions using dynamic parameter lookup
- Works **locally and offline**


## Scope

- Initial focus: **Copter**
- Architecture designed to support:
  - Plane
  - Rover
  - Sub


## Development Plan

- Convert existing prototype into modular, callable components
- Upgrade ML model to sequence-based HMM
- Integrate dynamic parameter retrieval from codebase
- Extend support to additional vehicle types
- Package as an easy-to-use CLI tool


## Final Goal

A simple command-line tool that:
- Runs locally (no internet required)
- Works on real-world logs
- Provides reliable root-cause diagnosis
- Remains open-source and extensible