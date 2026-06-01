"""
DeepFace API Service
Expone un endpoint HTTP para que n8n pueda generar embeddings faciales.
Requiere: pip install deepface flask numpy
"""

from flask import Flask, request, jsonify
import base64
import numpy as np
import io
import logging

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Importación lazy para evitar carga pesada en import
_deepface = None

def get_deepface():
    global _deepface
    if _deepface is None:
        from deepface import DeepFace
        _deepface = DeepFace
    return _deepface


def decode_image(base64_str: str) -> np.ndarray:
    """Decodifica imagen Base64 a array numpy."""
    import cv2
    # Eliminar prefijo data:image/... si existe
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]
    img_bytes = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("No se pudo decodificar la imagen")
    return img


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/embedding", methods=["POST"])
def get_embedding():
    """
    Recibe: { "image_base64": "..." }
    Devuelve: { "embedding": [...], "face_detected": true/false }
    """
    data = request.get_json(force=True)
    if not data or "image_base64" not in data:
        return jsonify({"error": "Se requiere 'image_base64'"}), 400

    try:
        img = decode_image(data["image_base64"])
        DeepFace = get_deepface()

        result = DeepFace.represent(
            img_path=img,
            model_name="Facenet512",   # Alta precisión, ~512 dims
            enforce_detection=False,
            detector_backend="opencv"
        )

        embedding = result[0]["embedding"]
        return jsonify({
            "embedding": embedding,
            "face_detected": True,
            "model": "Facenet512",
            "dims": len(embedding)
        })

    except ValueError as e:
        return jsonify({"error": str(e), "face_detected": False}), 422
    except Exception as e:
        logging.exception("Error procesando imagen")
        return jsonify({"error": str(e), "face_detected": False}), 500


@app.route("/verify", methods=["POST"])
def verify_faces():
    """
    Compara dos imágenes directamente.
    Recibe: { "img1_base64": "...", "img2_base64": "..." }
    """
    data = request.get_json(force=True)
    try:
        img1 = decode_image(data["img1_base64"])
        img2 = decode_image(data["img2_base64"])
        DeepFace = get_deepface()

        result = DeepFace.verify(
            img1_path=img1,
            img2_path=img2,
            model_name="Facenet512",
            distance_metric="cosine"
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)