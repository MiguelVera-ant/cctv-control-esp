"""
OpenCV Publisher - Captura rostros y los envía por MQTT como Base64
Requiere: pip install opencv-python paho-mqtt
"""

import cv2
import base64
import json
import time
import ssl
import paho.mqtt.client as mqtt

# ── Configuración ──────────────────────────────────────────
MQTT_BROKER   = "2451185979884d64a2d68ef51ec12921.s1.eu.hivemq.cloud"
MQTT_PORT     = 8883
MQTT_USER     = "hivemq.webclient.1780170530505"
MQTT_PASSWORD = "Ba!&FzfS7LQK0k2q3.$t"
MQTT_TOPIC    = "faces/detect"
MQTT_RESULT   = "faces/result"
DEVICE_ID     = "cam-01"
CAPTURE_FPS   = 1
FACE_MIN_SIZE = (80, 80)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def on_result(client, userdata, msg):
    try:
        result = json.loads(msg.payload.decode())
        status = result.get("status", "?")
        name   = result.get("person_name", result.get("message", ""))
        sim    = result.get("similarity", "")
        print(f"[RESULTADO] {status.upper()} | {name} | sim={sim}")
    except Exception as e:
        print(f"[ERROR] Resultado: {e}")

def encode_face(frame, x, y, w, h, padding=20) -> str:
    h_frame, w_frame = frame.shape[:2]
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(w_frame, x + w + padding)
    y2 = min(h_frame, y + h + padding)
    face_img = frame[y1:y2, x1:x2]
    _, buffer = cv2.imencode(".jpg", face_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode("utf-8")

def main():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_message = on_result
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.subscribe(MQTT_RESULT)
    client.loop_start()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la cámara")

    print(f"[INFO] Publicando en {MQTT_TOPIC} @ {MQTT_BROKER}:{MQTT_PORT}")
    last_send = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=FACE_MIN_SIZE)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        now = time.time()
        if len(faces) > 0 and (now - last_send) >= (1.0 / CAPTURE_FPS):
            x, y, w, h = faces[0]
            image_b64 = encode_face(frame, x, y, w, h)
            payload = json.dumps({
                "device_id":    DEVICE_ID,
                "image_base64": image_b64,
                "timestamp":    now
            })
            client.publish(MQTT_TOPIC, payload)
            print(f"[ENVIADO] Rostro {w}x{h}px → {MQTT_TOPIC}")
            last_send = now

        cv2.imshow("Detector de Rostros", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()

if __name__ == "__main__":
    main()