# IoT Smart Home Security System  
## Structured Test Plan & Live Demo Sequence

![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![IoT](https://img.shields.io/badge/IoT-Smart%20Home-green)
![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-orange)
![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-purple)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-yellow)
![Flask](https://img.shields.io/badge/Flask-Web%20API%20%2F%20Control%20Panel-black)

This document defines a **safe, structured testing order** for the IoT security system.  
The sequence progresses from **simple independent checks** to **complex alarm scenarios** to prevent state interference.

It can be used in two ways:

- **Live defense / demo sequence** (presentation flow)
- **Verification checklist** (home/CI-style manual testing)

---

## Scope

Covers verification for:

- Alarm logic (manual + armed-state scenarios)
- Motion-to-light automation (DPIR → DL)
- People counting (PIR + Ultrasonic fusion)
- Door switch hold alarms (DS1/DS2 held)
- Arming via membrane switch (DMS) with exit delay
- Entry delay and PIN handling
- Empty-house motion alarm
- Vibration alarm (GSG)
- LCD rotation (DHT1–DHT3)
- Kitchen timer (4SD)
- BRGB control (Web + IR)
- Web camera streaming (`/video_feed`)
- Telemetry + alarm event visualization (InfluxDB + Grafana)

---

## Test Observability (Required Monitors)

During all tests, observe **three parallel sources**:

1. **Web application status**
2. **Terminal logs** (simulation + server)
3. **Grafana** (alarm/telemetry visualization)

Useful web endpoints (as implemented in the repo):
- Control panel: `http://localhost:5000/control`
- System status: `http://localhost:5000/status`
- Camera stream: `http://localhost:5000/video_feed`

---

## Pre-Test Routine (Run Before Every Test Case)

1. Click **Reset test state**
2. Verify on `/control`:
   - `Alarm = OFF`
   - `System armed = NO`
   - `People count` is at its expected baseline
3. Click **Apply Test Config** (only if needed for the test case)
4. Keep Web UI + Terminal logs + Grafana visible throughout

> Tip: Always return to this baseline between major scenarios to avoid state bleed
> (especially people_count, armed state, and buzzer state).

---

## Recommended Testing Order (State-Safe Sequence)

### 1) Basic ALARM State Verification (Core Alarm Logic)

**Goal:** Validate the alarm turning ON/OFF and correct logging, independent of other automations.

**Settings**
- Disable auto alarm logic = **OFF**
- Enable:
  - GSG alarm = **ON**
  - DS hold alarm = **ON**
  - Empty room alarm = **ON**

**Action**
- Click **Trigger GSG**

**Expected**
- `Alarm = ON`
- Buzzer (DB) **active**
- Reason: `GSG_MANUAL`
- Alarm event appears in DB/Grafana

**Recovery**
- Enter PIN and click **Alarm OFF / Disarm**

**Expected**
- `Alarm = OFF`
- Buzzer (DB) **inactive**
- System disarmed

---

### 2) DPIR1 → DL (10-Second Logic)

**Goal:** Validate motion-to-light automation without security interference.

**Settings**
- Disable auto alarm logic = **ON**

**Action**
- Click **Trigger DPIR1**

**Expected**
- Door Light (DL) turns **ON**
- Door Light (DL) turns **OFF** after **~10 seconds**
- Logs contain ON/OFF timestamps that match the delay

---

### 3) People Counting (Sensor Fusion): DPIR1 + DUS1

**Goal:** Validate entry/exit inference using PIR trigger + ultrasonic distance threshold.

**Settings**
- Disable auto alarm logic = **ON**

#### 3.1 Entry
**Action**
- Ensure `DUS1` reports a **small distance** (below threshold)
- Trigger `DPIR1`

**Expected**
- `PEOPLE_COUNT` increments
- Action logged as: `ENTRY`

#### 3.2 Exit
**Action**
- Ensure `DUS1` reports a **large distance**
- Trigger `DPIR1`

**Expected**
- `PEOPLE_COUNT` decrements
- Action logged as: `EXIT`
- If `PEOPLE_COUNT == 0`, expected action: `EXIT_IGNORED`

**Repeat**
- Repeat both directions for **DPIR2 + DUS2**

---

### 4) DS1 / DS2 Held Alarm

**Goal:** Validate long-press alarm triggers without noise from other alarm types.

**Settings**
- Enable DS hold alarm = **ON**
- Others = **OFF**

**Action**
- Click **Trigger DS1 held**

**Expected**
- `Alarm = ON`
- Reason: `DS1_HELD_MANUAL`

**Repeat**
- Reset test state
- Click **Trigger DS2 held**
- Expected: `Alarm = ON`, Reason: `DS2_HELD_MANUAL`

---

### 5) DMS System Activation (Arming Countdown)

**Goal:** Validate arming workflow and exit delay.

**Action**
- Click **Arm System**

**Expected**
- System stays disarmed for **~10 seconds** (exit delay)
- Then transitions to: `System armed = YES`

---

### 6) Armed State + Entry Delay Scenario

**Goal:** Validate entry delay behavior and PIN success/failure path.

#### Test A — No PIN entered
**Steps**
1. Arm system
2. Wait until `System armed = YES`
3. Trigger `DS1` or `DS2`
4. Do **NOT** enter PIN

**Expected**
- Entry delay starts
- Alarm turns **ON** after timeout expires

#### Test B — Valid PIN entered
**Steps**
1. Arm system
2. Trigger `DS1` or `DS2`
3. Enter correct PIN **before** timeout

**Expected**
- Alarm remains **OFF**
- System disarms successfully

---

### 7) Empty House Alarm (Armed + Motion with people_count = 0)

**Goal:** Validate “armed + empty house + motion” alarm.

**Settings**
- Enable empty room alarm = **ON**
- Ensure `people_count = 0`

**Steps**
1. Arm system
2. Trigger `DPIR1` OR `DPIR2` OR `DPIR3`

**Expected**
- Alarm turns **ON**
- Reason indicates motion while empty + armed (implementation-specific naming)

---

### 8) GSG Alarm (Vibration / Movement)

**Goal:** Validate strong movement/vibration triggers alarm.

**Action**
- Click **Trigger GSG**

**Expected**
- Alarm turns **ON**
- Reason indicates GSG-triggered alarm (manual or armed-state depending on config)

---

### 9) LCD Rotation (DHT1–DHT3)

**Goal:** Validate climate sensor display rotation.

**Action**
- Run DHT simulation

**Expected**
- LCD cycles every few seconds
- Shows Temperature + Humidity sequentially for:
  - DHT1
  - DHT2
  - DHT3

---

### 10) Kitchen Timer (4-Digit 7-Segment Display — 4SD)

**Goal:** Validate timer set/add/expiry behaviors.

#### A) Web Set
**Action**
- Input `10` in web UI → **Set Timer**

**Expected**
- 4SD shows countdown time

#### B) Button Add
**Action**
- Press physical/simulated BTN

**Expected**
- Adds `N` seconds (per configuration; commonly +30s)
- Display updates accordingly

#### C) Expiry + Stop Blink
**Action**
- Wait until timer reaches `00:00`

**Expected**
- 4SD blinks `00:00`

**Action**
- Press BTN (or use stop-blink UI/API if exposed)

**Expected**
- Blinking stops

---

### 11) BRGB Control (Web + IR)

**Goal:** Validate RGB LED stays synchronized across control channels.

#### Web Control
**Actions**
- Toggle ON/OFF
- Change colors

**Expected**
- Physical/simulated BRGB state matches UI state

#### IR Control
**Actions**
- Send IR remote commands (simulated):
  - ON / OFF
  - RED / GREEN (and other supported colors)

**Expected**
- UI and BRGB remain synchronized after IR commands

---

### 12) Web Camera

**Goal:** Validate camera feed availability on the control panel.

**Action**
- Navigate to `/control` and verify `/video_feed`

**Expected**
- Live video stream visible and updating

---

## Final Demo Sequence (Presentation Flow)

Recommended “smooth show” order:

1. Web App (Status & Camera)
2. DPIR1 → DL (10s)
3. People Count (Entry/Exit logic)
4. DS1/DS2 Held Alarms
5. Arming via DMS (Countdown)
6. Armed + DS trigger + PIN timeout logic
7. Empty House + PIR Alarm
8. GSG Alarm
9. LCD Rotation
10. Kitchen Timer (Set/Add/Blink/Stop)
11. BRGB (Web + IR)
12. Grafana Dashboards (show alarm events & timelines)

---

## Debugging & Configuration Tips

- **Isolation Principle:** When testing a specific alarm type (DS hold, GSG, empty room), disable other alarm types to prevent “ghost triggers”.
- **Manual Override:** Use **Disable auto alarm logic = ON** when validating UI/actuators (Timer, BRGB) to avoid accidental security escalation.
- **State hygiene:** Always reset between scenarios that affect `armed`, `alarm`, or `people_count`.

---

## Notes / Space for Test Evidence

Use this section to paste artifacts from real runs:

- Screenshot(s) of `/control`
- Terminal log excerpts (timestamps)
- Grafana panel screenshot(s) showing the alarm event