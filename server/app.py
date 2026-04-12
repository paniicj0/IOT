import json
import threading
from flask import Flask, jsonify, Response, request

from mqtt_listener import start_mqtt
from influx_writer import InfluxWriter
from mqtt_publisher import MqttCmdPublisher


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


app = Flask(__name__)

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


def update_state_from_record(rec: dict):
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


def send_cmd(topic: str, payload: dict):
    cmd_pub.send(topic, payload)


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
    send_cmd(PI1_TOPIC, {"device": "DMS", "action": "pin", "pin": pin})
    return jsonify({"ok": True, "sent": {"device": "DMS", "action": "pin"}})

@app.post("/alarm/arm")
def alarm_arm():
    send_cmd(PI1_TOPIC, {"device": "DMS", "action": "arm"})
    return jsonify({"ok": True, "sent": {"device": "DMS", "action": "arm"}})


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
    send_cmd(PI1_TOPIC, {"device": "DMS", "action": "pin", "pin": pin})
    return jsonify({"ok": True, "sent": {"device": "DMS", "action": "pin", "pin": pin}})

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

        async function refreshStatus() {
          try {
            const r = await fetch('/status');
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

            setTimeout(refreshStatus, 400);
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
          const pin = document.getElementById('pin').value || '1234';
          post('/alarm/pin?pin=' + encodeURIComponent(pin));
        }

        function timerSet() {
          const s = document.getElementById('timerSet').value || 0;
          post('/timer/set/' + s);
        }

        function timerAdd() {
          const s = document.getElementById('timerAdd').value || 0;
          post('/timer/add/' + s);
        }

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