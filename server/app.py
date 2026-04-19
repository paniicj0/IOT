import json
import threading
from flask import Flask, jsonify, Response, request

from mqtt_listener import start_mqtt
from influx_writer import InfluxWriter
from mqtt_publisher import MqttCmdPublisher

import cv2


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


app = Flask(__name__)
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

cfg = load_config()
influx = cfg["influx"]
mqtt_cfg = cfg["mqtt"]

writer = InfluxWriter(
    url=influx["url"],
    token=influx["token"],
    org=influx["org"],
    bucket=influx["bucket"]
)

cmd_pub = MqttCmdPublisher(mqtt_cfg["host"], mqtt_cfg["port"])

PI1_TOPIC = "iot/pi1/actuators"
PI2_TOPIC = "iot/pi2/actuators"
PI3_TOPIC = "iot/pi3/actuators"

state_lock = threading.Lock()
latest_state = {
    "alarm_active": 0,
    "alarm_reason": "",
    "system_armed": False,
    "people_count": 0,
    "timer_seconds": 0,
    "timer_blinking": False,
    "brgb_on": False,
    "brgb_color": "OFF",
    "sensors": {}
}

test_config_lock = threading.Lock()
test_config = {
    "manual_mode": False,
    "disable_alarm_logic": False,
    "allow_gsg_alarm": True,
    "allow_ds_hold_alarm": True,
    "allow_empty_room_alarm": True
}


def update_state_from_record(rec: dict):
    print("[SERVER RAW RECORD]", rec)
    sensor = rec.get("sensor")
    value = rec.get("value")
    pi_id = rec.get("pi_id", "")
    ts = rec.get("timestamp", "")

    with state_lock:
        latest_state["sensors"][sensor] = {
            "pi_id": pi_id,
            "value": value,
            "timestamp": ts
        }

        if sensor == "ALARM_STATUS" and isinstance(value, dict):
            latest_state["alarm_active"] = int(value.get("active", 0))
            latest_state["alarm_reason"] = str(value.get("reason", ""))
        
        elif sensor == "SYSTEM_ARMED" and isinstance(value, dict):
            latest_state["system_armed"] = bool(value.get("armed", 0))

        elif sensor == "PEOPLE_COUNT" and isinstance(value, dict):
            latest_state["people_count"] = int(value.get("count", 0))

        elif sensor == "BRGB_STATE" and isinstance(value, dict):
            latest_state["brgb_on"] = bool(value.get("is_on", False))
            latest_state["brgb_color"] = str(value.get("color", "OFF"))

        elif sensor == "4SD" and isinstance(value, dict):
          latest_state["timer_seconds"] = int(value.get("seconds", 0))
          latest_state["timer_blinking"] = bool(value.get("blinking", False))
          print("[SERVER] 4SD UPDATE =", latest_state["timer_seconds"], latest_state["timer_blinking"])


def send_cmd(topic: str, payload: dict):
    cmd_pub.send(topic, payload)

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            continue

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/status")
def status():
    with state_lock:
        return jsonify(latest_state)


@app.post("/actuators/<device>/<action>")
def actuators(device, action):
    if device not in ("DL", "DB") or action not in ("on", "off"):
        return jsonify({"ok": False, "error": "bad params"}), 400

    send_cmd(PI1_TOPIC, {"device": device, "action": action})
    return jsonify({"ok": True, "sent": {"device": device, "action": action}})


@app.post("/alarm/off")
def alarm_off():
    pin = request.args.get("pin", "1234")
    payload = {"device": "DMS", "action": "pin", "pin": pin}

    send_cmd(PI1_TOPIC, payload)
    send_cmd(PI2_TOPIC, payload)
    send_cmd(PI3_TOPIC, payload)

    return jsonify({
        "ok": True,
        "sent": {
            "device": "DMS",
            "action": "pin",
            "pin": pin,
            "targets": ["PI1", "PI2", "PI3"]
        }
    })

@app.post("/alarm/arm")
def alarm_arm():
    send_cmd(PI1_TOPIC, {"device": "DMS", "action": "arm"})
    send_cmd(PI2_TOPIC, {"device": "DMS", "action": "arm"})
    send_cmd(PI3_TOPIC, {"device": "DMS", "action": "arm"})

    return jsonify({
        "ok": True,
        "sent": {
            "device": "DMS",
            "action": "arm",
            "targets": ["PI1", "PI2", "PI3"]
        }
    })


@app.get("/test-config")
def get_test_config():
    with test_config_lock:
        return jsonify(test_config)


@app.post("/test-config")
def set_test_config():
    global test_config

    data = request.get_json(force=True) or {}

    with test_config_lock:
        test_config["manual_mode"] = bool(data.get("manual_mode", False))
        test_config["disable_alarm_logic"] = bool(data.get("disable_alarm_logic", False))
        test_config["allow_gsg_alarm"] = bool(data.get("allow_gsg_alarm", True))
        test_config["allow_ds_hold_alarm"] = bool(data.get("allow_ds_hold_alarm", True))
        test_config["allow_empty_room_alarm"] = bool(data.get("allow_empty_room_alarm", True))

        current_config = dict(test_config)

    payload = {
        "device": "TEST_CONFIG",
        "action": "set",
        "config": current_config
    }

    send_cmd(PI1_TOPIC, payload)
    send_cmd(PI2_TOPIC, payload)
    send_cmd(PI3_TOPIC, payload)

    return jsonify({
        "ok": True,
        "config": current_config,
        "sent_to": ["PI1", "PI2", "PI3"]
    })


@app.post("/test-trigger/<name>")
def test_trigger(name):
    allowed = {
        "gsg": {"device": "TEST_TRIGGER", "action": "gsg"},
        "ds1_held": {"device": "TEST_TRIGGER", "action": "ds1_held"},
        "ds2_held": {"device": "TEST_TRIGGER", "action": "ds2_held"},
        "dpir1": {"device": "TEST_TRIGGER", "action": "dpir1"},
        "reset": {"device": "TEST_TRIGGER", "action": "reset"}
    }

    if name not in allowed:
        return jsonify({"ok": False, "error": "bad trigger"}), 400

    payload = allowed[name]

    send_cmd(PI1_TOPIC, payload)
    send_cmd(PI2_TOPIC, payload)
    send_cmd(PI3_TOPIC, payload)

    return jsonify({
        "ok": True,
        "sent": payload,
        "targets": ["PI1", "PI2", "PI3"]
    })


@app.post("/timer/set/<int:seconds>")
def timer_set(seconds):
    send_cmd(PI2_TOPIC, {"device": "4SD", "action": "set", "seconds": seconds})
    return jsonify({"ok": True, "sent": {"device": "4SD", "action": "set", "seconds": seconds}})


@app.post("/timer/add/<int:seconds>")
def timer_add(seconds):
    send_cmd(PI2_TOPIC, {"device": "4SD", "action": "add", "seconds": seconds})
    return jsonify({"ok": True, "sent": {"device": "4SD", "action": "add", "seconds": seconds}})


@app.post("/timer/stop-blink")
def timer_stop_blink():
    send_cmd(PI2_TOPIC, {"device": "4SD", "action": "stop_blink"})
    return jsonify({"ok": True, "sent": {"device": "4SD", "action": "stop_blink"}})


@app.post("/brgb/on")
def brgb_on():
    send_cmd(PI3_TOPIC, {"device": "BRGB", "action": "on"})
    return jsonify({"ok": True, "sent": {"device": "BRGB", "action": "on"}})


@app.post("/brgb/off")
def brgb_off():
    send_cmd(PI3_TOPIC, {"device": "BRGB", "action": "off"})
    return jsonify({"ok": True, "sent": {"device": "BRGB", "action": "off"}})


@app.post("/brgb/color/<color>")
def brgb_color(color):
    color = color.upper()
    allowed = {"RED", "GREEN", "BLUE", "WHITE", "YELLOW", "PURPLE"}
    if color not in allowed:
        return jsonify({"ok": False, "error": "bad color"}), 400

    send_cmd(PI3_TOPIC, {"device": "BRGB", "action": "set_color", "color": color})
    return jsonify({"ok": True, "sent": {"device": "BRGB", "action": "set_color", "color": color}})


@app.post("/alarm/pin")
def alarm_pin():
    pin = request.args.get("pin", "1234")

    payload = {"device": "DMS", "action": "pin", "pin": pin}

    send_cmd(PI1_TOPIC, payload)
    send_cmd(PI2_TOPIC, payload)
    send_cmd(PI3_TOPIC, payload)

    return jsonify({
        "ok": True,
        "sent": {
            "device": "DMS",
            "action": "pin",
            "pin": pin,
            "targets": ["PI1", "PI2", "PI3"]
        }
    })

@app.get("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.get("/control")
def control():
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <title>IoT Smart Home Control</title>
      <style>
        body{
          font-family:Arial,sans-serif;
          background:#0f1115;
          color:#eee;
          margin:0;
          padding:20px;
        }
        h1{
          margin:0 0 6px 0;
        }
        .sub{
          opacity:.8;
          margin-bottom:18px;
        }
        .grid{
          display:grid;
          grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
          gap:16px;
        }
        .card{
          background:#1a1f29;
          border-radius:14px;
          padding:16px;
          box-shadow:0 2px 10px rgba(0,0,0,.25);
        }
        .status-card{
          border:2px solid #2c3442;
        }
        .alarm-on{
          border-color:#ff5c5c !important;
          box-shadow:0 0 0 1px rgba(255,92,92,.2), 0 0 18px rgba(255,92,92,.18);
        }
        .alarm-off{
          border-color:#35c26b !important;
          box-shadow:0 0 0 1px rgba(53,194,107,.15), 0 0 18px rgba(53,194,107,.10);
        }
        h3{
          margin:0 0 12px 0;
        }
        button{
          padding:10px 14px;
          margin:6px 6px 0 0;
          border:0;
          border-radius:10px;
          cursor:pointer;
          font-weight:600;
        }
        input, select{
          padding:10px;
          border-radius:10px;
          border:1px solid #444;
          background:#111;
          color:#eee;
          margin-top:6px;
        }
        .row{
          margin-top:12px;
        }
        .ok{ color:#7CFC98; }
        .err{ color:#ff7b7b; }
        .muted{ opacity:.8; }
        .status-line{
          margin:8px 0;
          font-size:15px;
        }
        .label{
          opacity:.75;
          display:inline-block;
          min-width:130px;
        }
        .big{
          font-size:24px;
          font-weight:700;
        }
        .pill{
          display:inline-block;
          padding:4px 10px;
          border-radius:999px;
          font-size:13px;
          font-weight:700;
        }
        .pill-red{ background:#5a1f1f; color:#ffb3b3; }
        .pill-green{ background:#183d28; color:#aaf0c4; }
        .pill-blue{ background:#1e3557; color:#b7d8ff; }
        .pill-yellow{ background:#5a4a16; color:#ffe58f; }
        .pill-purple{ background:#4a235a; color:#ebc7ff; }
        .pill-gray{ background:#333; color:#ddd; }
        .resp-box{
          min-height:70px;
          white-space:pre-wrap;
          word-break:break-word;
          background:#111;
          border-radius:10px;
          padding:10px;
        }
        a{ color:#8ecbff; }
      </style>
    </head>
    <body>
      <h1>IoT Smart Home Control</h1>
      <div class="sub">Status + osnovne kontrole za odbranu</div>

      <div class="grid">
        <div id="statusCard" class="card status-card alarm-off">
          <h3>System status</h3>

          <div class="status-line">
            <span class="label">Alarm:</span>
            <span id="alarmBadge" class="pill pill-green">OFF</span>
          </div>

          <div class="status-line">
            <span class="label">System armed:</span>
            <span id="armedBadge" class="pill pill-gray">NO</span>
          </div>

          <div class="status-line">
            <span class="label">Reason:</span>
            <span id="alarmReason">-</span>
          </div>

          <div class="status-line">
            <span class="label">People count:</span>
            <span id="peopleCount" class="big">0</span>
          </div>

          <div class="status-line">
            <span class="label">Timer:</span>
            <span id="timerValue">0 s</span>
          </div>

          <div class="status-line">
            <span class="label">Blinking:</span>
            <span id="timerBlink">False</span>
          </div>

          <div class="status-line">
            <span class="label">BRGB:</span>
            <span id="brgbState" class="pill pill-gray">OFF</span>
          </div>

          <div class="status-line">
            <span class="label">BRGB color:</span>
            <span id="brgbColor">OFF</span>
          </div>

          <div class="status-line">
            <span class="label">Updated:</span>
            <span id="lastRefresh">-</span>
          </div>

          <div class="row">
            <a href="http://localhost:3000" target="_blank">Open Grafana</a>
          </div>
        </div>

        <div class="card">
          <h3>PI1 - Door actuators</h3>
          <button onclick="post('/actuators/DL/on')">DL ON</button>
          <button onclick="post('/actuators/DL/off')">DL OFF</button>
          <br/>
          <button onclick="post('/actuators/DB/on')">DB ON</button>
          <button onclick="post('/actuators/DB/off')">DB OFF</button>
        </div>

        <div class="card">
          <h3>Alarm</h3>
          <div class="muted">PIN komande za arm/disarm sistema</div>
          <input id="pin" value="1234" placeholder="PIN"/>
          <div class="row">
            <button onclick="alarmArm()">Arm System</button>
            <button onclick="alarmOff()">Alarm OFF / Disarm</button>
          </div>
        </div>

        <div class="card">
          <h3>Test mode</h3>
          <div class="muted">Kontrola simulacije za odbranu</div>

          <div class="row">
            <label><input type="checkbox" id="manualMode"> Manual test mode</label>
          </div>

          <div class="row">
            <label><input type="checkbox" id="disableAlarmLogic"> Disable auto alarm logic</label>
          </div>

          <div class="row">
            <label><input type="checkbox" id="allowGsgAlarm" checked> Enable GSG alarm</label>
          </div>

          <div class="row">
            <label><input type="checkbox" id="allowDsHoldAlarm" checked> Enable DS hold alarm</label>
          </div>

          <div class="row">
            <label><input type="checkbox" id="allowEmptyRoomAlarm" checked> Enable empty room alarm</label>
          </div>

          <div class="row">
            <button onclick="applyTestConfig()">Apply Test Config</button>
          </div>

          <div class="row">
            <button onclick="post('/test-trigger/gsg')">Trigger GSG</button>
            <button onclick="post('/test-trigger/ds1_held')">Trigger DS1 held</button>
          </div>

          <div class="row">
            <button onclick="post('/test-trigger/ds2_held')">Trigger DS2 held</button>
            <button onclick="post('/test-trigger/dpir1')">Trigger DPIR1</button>
          </div>

          <div class="row">
            <button onclick="post('/test-trigger/reset')">Reset test state</button>
          </div>
        </div>

        <div class="card">
          <h3>PI2 - Timer</h3>
          <div class="muted">Set početnog vremena</div>
          <input id="timerSet" type="number" value="120" min="0"/>
          <button onclick="timerSet()">Set Timer</button>
          <div class="row muted">Dodavanje sekundi</div>
          <input id="timerAdd" type="number" value="30" min="0"/>
          <button onclick="timerAdd()">Add Seconds</button>
          <button onclick="post('/timer/stop-blink')">Stop Blink</button>
        </div>

        <div class="card">
          <h3>PI3 - BRGB</h3>
          <button onclick="post('/brgb/on')">ON</button>
          <button onclick="post('/brgb/off')">OFF</button>
          <br/>
          <button onclick="post('/brgb/color/RED')">RED</button>
          <button onclick="post('/brgb/color/GREEN')">GREEN</button>
          <button onclick="post('/brgb/color/BLUE')">BLUE</button>
          <button onclick="post('/brgb/color/WHITE')">WHITE</button>
          <button onclick="post('/brgb/color/YELLOW')">YELLOW</button>
          <button onclick="post('/brgb/color/PURPLE')">PURPLE</button>
        </div>

        <div class="card">
          <h3>Response</h3>
          <div id="resp" class="resp-box ok">ready</div>
        </div>

        <div class="card">
          <h3>Camera</h3>
          <img src="/video_feed" style="width:100%; border-radius:12px;" />
        </div>

        <div class="card">
          <div style="border-radius: 12px; overflow: hidden;">
            <iframe src="http://localhost:3000/d-solo/ad5frfd/vizualization?orgId=1&from=1776596248743&to=1776597148743&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
            <iframe src="http://localhost:3000/d-solo/ad5scfs/door-sensors?orgId=1&from=1776510654448&to=1776597054448&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
          </div>
        </div>

        <div class="card">
          <div style="border-radius: 12px; overflow: hidden;">
            <iframe src="http://localhost:3000/d-solo/adc727n/alarm?orgId=1&from=1776597663817&to=1776598563817&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
            <iframe src="http://localhost:3000/d-solo/adh4t49/alarm-over-time?orgId=1&from=1776576986940&to=1776598586940&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
          </div>
        </div>

        <div class="card">
          <div style="border-radius: 12px; overflow: hidden;">
            <iframe src="http://localhost:3000/d-solo/adgtm47/temperature?orgId=1&from=1776577216991&to=1776598816991&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
            <iframe src="http://localhost:3000/d-solo/adjjwf5/people-count?orgId=1&from=1776597965239&to=1776598865239&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
          </div>
        </div>

        <div class="card">
          <div style="border-radius: 12px; overflow: hidden;">
            <iframe src="http://localhost:3000/d-solo/addhzfc/motion-dpir?orgId=1&from=1776588093174&to=1776598893174&timezone=browser&panelId=panel-1&__feature.dashboardSceneSolo=true" width="450" height="200" frameborder="0"></iframe>
          </div>
        </div>


        
        
      </div>

      <script>
        function colorClassForBrgb(color, isOn) {
          if (!isOn) return 'pill pill-gray';
          switch ((color || '').toUpperCase()) {
            case 'RED': return 'pill pill-red';
            case 'GREEN': return 'pill pill-green';
            case 'BLUE': return 'pill pill-blue';
            case 'YELLOW': return 'pill pill-yellow';
            case 'PURPLE': return 'pill pill-purple';
            case 'WHITE': return 'pill pill-blue';
            default: return 'pill pill-gray';
          }
        }

        async function loadTestConfig() {
          try {
            const r = await fetch('/test-config', { cache: 'no-store' });
            const j = await r.json();

            document.getElementById('manualMode').checked = !!j.manual_mode;
            document.getElementById('disableAlarmLogic').checked = !!j.disable_alarm_logic;
            document.getElementById('allowGsgAlarm').checked = !!j.allow_gsg_alarm;
            document.getElementById('allowDsHoldAlarm').checked = !!j.allow_ds_hold_alarm;
            document.getElementById('allowEmptyRoomAlarm').checked = !!j.allow_empty_room_alarm;
          } catch (e) {
            console.log('test config load error', e);
          }
        }

        async function applyTestConfig() {
          const resp = document.getElementById('resp');
          resp.className = 'resp-box ok';
          resp.textContent = 'sending test config...';

          const body = {
            manual_mode: document.getElementById('manualMode').checked,
            disable_alarm_logic: document.getElementById('disableAlarmLogic').checked,
            allow_gsg_alarm: document.getElementById('allowGsgAlarm').checked,
            allow_ds_hold_alarm: document.getElementById('allowDsHoldAlarm').checked,
            allow_empty_room_alarm: document.getElementById('allowEmptyRoomAlarm').checked
          };

          try {
            const r = await fetch('/test-config', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(body)
            });

            const j = await r.json();

            if (!r.ok) {
              resp.className = 'resp-box err';
              resp.textContent = JSON.stringify(j, null, 2);
            } else {
              resp.className = 'resp-box ok';
              resp.textContent = JSON.stringify(j, null, 2);
            }

              setTimeout(refreshStatus, 800);
            } catch (e) {
              resp.className = 'resp-box err';
              resp.textContent = 'error: ' + e;
            }
          }

        async function refreshStatus() {
          try {
            const r = await fetch('/status', { cache: 'no-store' });
            const j = await r.json();

            const alarmOn = Number(j.alarm_active) === 1;
            const armed = !!j.system_armed;
            const armedBadge = document.getElementById('armedBadge');
            armedBadge.textContent = armed ? 'YES' : 'NO';
            armedBadge.className = armed ? 'pill pill-blue' : 'pill pill-gray';
            const alarmBadge = document.getElementById('alarmBadge');
            const statusCard = document.getElementById('statusCard');

            alarmBadge.textContent = alarmOn ? 'ON' : 'OFF';
            alarmBadge.className = alarmOn ? 'pill pill-red' : 'pill pill-green';

            statusCard.classList.remove('alarm-on', 'alarm-off');
            statusCard.classList.add(alarmOn ? 'alarm-on' : 'alarm-off');

            document.getElementById('alarmReason').textContent = j.alarm_reason || '-';
            document.getElementById('peopleCount').textContent = j.people_count ?? 0;
            document.getElementById('timerValue').textContent = `${j.timer_seconds ?? 0} s`;
            document.getElementById('timerBlink').textContent = String(j.timer_blinking ?? false);

            const brgbOn = !!j.brgb_on;
            const brgbColor = j.brgb_color || 'OFF';
            const brgbState = document.getElementById('brgbState');
            brgbState.textContent = brgbOn ? 'ON' : 'OFF';
            brgbState.className = colorClassForBrgb(brgbColor, brgbOn);

            document.getElementById('brgbColor').textContent = brgbColor;
            document.getElementById('lastRefresh').textContent = new Date().toLocaleTimeString();
          } catch (e) {
            document.getElementById('resp').className = 'resp-box err';
            document.getElementById('resp').textContent = 'status error: ' + e;
          }
        }

        async function post(url) {
          const resp = document.getElementById('resp');
          resp.className = 'resp-box ok';
          resp.textContent = 'sending...';

          try {
            const r = await fetch(url, {method: 'POST'});
            const j = await r.json();

            if (!r.ok) {
              resp.className = 'resp-box err';
              resp.textContent = JSON.stringify(j, null, 2);
            } else {
              resp.className = 'resp-box ok';
              resp.textContent = JSON.stringify(j, null, 2);
            }

            setTimeout(refreshStatus, 1500);
          } catch (e) {
            resp.className = 'resp-box err';
            resp.textContent = 'error: ' + e;
          }
        }

        function alarmOff() {
          const pin = document.getElementById('pin').value || '1234';
          post('/alarm/pin?pin=' + encodeURIComponent(pin));
        }

        function alarmArm() {
          post('/alarm/arm');
        }

        function timerSet() {
          const s = document.getElementById('timerSet').value || 0;
          post('/timer/set/' + s);
        }

        function timerAdd() {
          const s = document.getElementById('timerAdd').value || 0;
          post('/timer/add/' + s);
        }

        loadTestConfig();
        refreshStatus();
        setInterval(refreshStatus, 2000);
      </script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")

def mqtt_worker():
    print("Server started (MQTT -> InfluxDB)")
    start_mqtt(
        writer,
        host=mqtt_cfg["host"],
        port=mqtt_cfg["port"],
        topic="iot/+/sensors",
        on_record=update_state_from_record
    )


if __name__ == "__main__":
    t = threading.Thread(target=mqtt_worker, daemon=True)
    t.start()

    print("HTTP control page: http://localhost:5000/control")
    app.run(host="0.0.0.0", port=5000, debug=False)