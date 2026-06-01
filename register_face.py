"""
register_face.py — Registra rostros en Supabase usando DeepFace local

Uso:
    python register_face.py --name "Tu Nombre"
    python register_face.py --name "Tu Nombre" --person-id "uuid-existente"  # agrega más fotos a una persona
    python register_face.py --list   # lista personas registradas

Requiere:
    pip install opencv-python requests psycopg2-binary
"""

import cv2
import base64
import requests
import psycopg2
import argparse
import json
import sys
import time

# ── Configuración ──────────────────────────────────────────────────────────────
DEEPFACE_URL = "http://localhost:5001/embedding"

# Datos de conexión a Supabase (edita estos valores)
DB_HOST     = "aws-1-us-east-2.pooler.supabase.com"  # <-- cambia esto
DB_PORT     = 6543
DB_NAME     = "postgres"
DB_USER     = "postgres.wyqurpkuxtcuokxxugkq"
DB_PASSWORD = "Konrad206++*"                       # <-- cambia esto
# ──────────────────────────────────────────────────────────────────────────────


def conectar_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=DB_NAME, user=DB_USER,
        password=DB_PASSWORD, sslmode="require"
    )


def capturar_rostro():
    """Abre la cámara, espera que el usuario presione ESPACIO para capturar, Q para salir."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la cámara")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    print("\n[CÁMARA] Mira a la cámara y presiona ESPACIO para capturar, Q para cancelar\n")
    captured = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        status = f"Rostros detectados: {len(faces)} | ESPACIO=capturar  Q=salir"
        cv2.putText(frame, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow("Registro de Rostro", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            if len(faces) == 0:
                print("[AVISO] No se detectó ningún rostro, intenta de nuevo")
                continue
            captured = frame.copy()
            print("[OK] Rostro capturado")
            break

    cap.release()
    cv2.destroyAllWindows()
    return captured


def imagen_a_base64(frame):
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buffer).decode('utf-8')


def obtener_embedding(image_b64):
    print("[INFO] Enviando imagen a DeepFace...")
    try:
        resp = requests.post(DEEPFACE_URL, json={"image_base64": image_b64}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "embedding" not in data:
            print(f"[ERROR] Respuesta inesperada de DeepFace: {data}")
            return None
        return data["embedding"]
    except requests.exceptions.ConnectionError:
        print("[ERROR] No se pudo conectar a DeepFace en localhost:5001")
        print("        Verifica que los contenedores Docker están corriendo: docker compose ps")
        return None
    except Exception as e:
        print(f"[ERROR] DeepFace: {e}")
        return None


def crear_persona(conn, nombre):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO persons (name, metadata) VALUES (%s, %s) RETURNING id",
            (nombre, json.dumps({}))
        )
        person_id = cur.fetchone()[0]
        conn.commit()
    print(f"[DB] Persona creada: {nombre} → {person_id}")
    return str(person_id)


def guardar_embedding(conn, person_id, embedding, image_b64):
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO face_embeddings (person_id, embedding, image_base64, confidence)
               VALUES (%s, %s::vector, %s, %s) RETURNING id""",
            (person_id, embedding_str, image_b64, 1.0)
        )
        face_id = cur.fetchone()[0]
        conn.commit()
    print(f"[DB] Embedding guardado: {face_id}")
    return str(face_id)


def listar_personas(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.id, p.name, COUNT(fe.id) as fotos, p.created_at
            FROM persons p
            LEFT JOIN face_embeddings fe ON fe.person_id = p.id
            GROUP BY p.id, p.name, p.created_at
            ORDER BY p.created_at DESC
        """)
        rows = cur.fetchall()

    if not rows:
        print("\nNo hay personas registradas aún.\n")
        return

    print(f"\n{'ID':<38} {'Nombre':<20} {'Fotos':<8} {'Creado'}")
    print("─" * 80)
    for row in rows:
        print(f"{str(row[0]):<38} {row[1]:<20} {row[2]:<8} {str(row[3])[:19]}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Registra rostros en Supabase")
    parser.add_argument("--name", help="Nombre de la persona a registrar")
    parser.add_argument("--person-id", help="UUID de persona existente (para agregar más fotos)")
    parser.add_argument("--list", action="store_true", help="Lista personas registradas")
    args = parser.parse_args()

    # Conectar DB
    try:
        conn = conectar_db()
        print("[DB] Conexión a Supabase exitosa")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a Supabase: {e}")
        sys.exit(1)

    if args.list:
        listar_personas(conn)
        conn.close()
        return

    if not args.name and not args.person_id:
        parser.print_help()
        print("\nEjemplos:")
        print('  python register_face.py --name "Juan Pérez"')
        print('  python register_face.py --name "Juan Pérez" --person-id "uuid-aqui"')
        print('  python register_face.py --list')
        conn.close()
        sys.exit(0)

    # Determinar person_id
    if args.person_id:
        person_id = args.person_id
        print(f"[INFO] Agregando foto a persona existente: {person_id}")
    else:
        person_id = crear_persona(conn, args.name)

    # Capturar rostro
    frame = capturar_rostro()
    if frame is None:
        print("[CANCELADO] No se capturó ningún rostro")
        conn.close()
        sys.exit(0)

    # Generar embedding
    image_b64 = imagen_a_base64(frame)
    embedding = obtener_embedding(image_b64)
    if embedding is None:
        conn.close()
        sys.exit(1)

    print(f"[INFO] Embedding generado ({len(embedding)} dimensiones)")

    # Guardar en DB
    face_id = guardar_embedding(conn, person_id, embedding, image_b64)
    conn.close()

    print(f"\n✅ Registro completo")
    print(f"   Persona : {args.name or person_id}")
    print(f"   Person ID: {person_id}")
    print(f"   Face ID  : {face_id}")
    print(f"\nPuedes registrar más fotos de la misma persona con:")
    print(f'   python register_face.py --name "{args.name or "Nombre"}" --person-id "{person_id}"')


if __name__ == "__main__":
    main()