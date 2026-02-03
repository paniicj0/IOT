import json
import threading
from flask import Flask, jsonify, Response

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

# Influx writer
writer = InfluxWriter(
    url=influx["url"],
    token=influx["token"],
    org=influx["org"],
    bucket=influx["bucket"]
)

# MQTT publisher za komande (aktuatori)
cmd_pub = MqttCmdPublisher(mqtt_cfg["host"], mqtt_cfg["port"])
ACT_TOPIC = mqtt_cfg.get("topic_actuators", "iot/pi1/actuators")


@app.post("/actuators/<device>/<action>")
def actuators(device, action):
    # device: DL (door light) ili DB (buzzer)
    # action: on/off
    if device not in ("DL", "DB") or action not in ("on", "off"):
        return jsonify({"ok": False, "error": "bad params"}), 400

    cmd_pub.send(ACT_TOPIC, {"device": device, "action": action})
    return jsonify({"ok": True, "sent": {"device": device, "action": action}})


@app.get("/control")
def control():
    # strana koju ubacujemo u Grafanu preko iframe-a
    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <style>
        body{{font-family:Arial;padding:12px;background:#111;color:#eee;margin:0}}
        .card{{background:#1b1b1b;padding:12px;border-radius:12px}}
        button{{padding:10px 14px;margin:6px;border:0;border-radius:10px;cursor:pointer}}
        .row{{margin-top:10px}}
        .ok{{color:#8ef}}
        .err{{color:#f88}}
        small{{opacity:.7}}
      </style>
    </head>
    <body>
      <div class="card">
        <h3 style="margin:0 0 8px 0">PI1 Actuators</h3>
        <small>MQTT topic: {ACT_TOPIC}</small>

        <div class="row">
          <strong>Door light (DL)</strong><br/>
          <button onclick="sendCmd('DL','on')">Light ON</button>
          <button onclick="sendCmd('DL','off')">Light OFF</button>
        </div>

        <div class="row">
          <strong>Buzzer (DB)</strong><br/>
          <button onclick="sendCmd('DB','on')">Buzzer ON</button>
          <button onclick="sendCmd('DB','off')">Buzzer OFF</button>
        </div>

        <div class="row">
          <strong>Status:</strong>
          <div id="st" class="ok">ready</div>
        </div>
      </div>

      <script>
        async function sendCmd(dev, act) {{
          const st = document.getElementById('st');
          st.className = "ok";
          st.textContent = "sending...";
          try {{
            const r = await fetch(`/actuators/${{dev}}/${{act}}`, {{method:'POST'}});
            const j = await r.json();
            if (!r.ok) {{
              st.className = "err";
              st.textContent = JSON.stringify(j);
            }} else {{
              st.className = "ok";
              st.textContent = "sent: " + JSON.stringify(j.sent);
            }}
          }} catch(e) {{
            st.className = "err";
            st.textContent = "error: " + e;
          }}
        }}
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
        topic=mqtt_cfg["topic"]
    )


if __name__ == "__main__":
    # MQTT worker u daemon thread-u (ne blokira Flask)
    t = threading.Thread(target=mqtt_worker, daemon=True)
    t.start()

    print("HTTP control page: http://localhost:5000/control")
    app.run(host="0.0.0.0", port=5000, debug=False)
