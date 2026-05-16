# Face Recognition Stack — Docker

## Estructura

```
face-recognition-docker/
├── docker-compose.yml       # Orquestación principal
├── .env.example             # Variables de entorno
├── Makefile                 # Comandos rápidos
├── config/
│   └── mosquitto.conf       # Config del broker MQTT
└── deepface/
    ├── Dockerfile
    ├── requirements.txt
    └── deepface_api.py      # API Flask de reconocimiento
```

## Pasos para levantar

### 1. Requisitos

- Docker >= 24
- Docker Compose >= 2.x
- 4 GB RAM mínimo (DeepFace carga modelos pesados)

### 2. Configurar variables

```bash
cp .env.example .env
# Editar .env con tu editor preferido
```

### 3. Build e inicio

```bash
make build
make up

# Verificar que todo está corriendo
make status
```

### 4. Importar workflow en n8n

- Abre http://localhost:5678
- Settings → Import Workflow → sube n8n_workflow.json
- Configura las credenciales:
  - **MQTT**: host=mosquitto, port=1883
  - **Postgres**: datos de tu Supabase

### 5. Ajustar URL de DeepFace en n8n

En el nodo "DeepFace - Generar Embedding", la URL debe ser:

```
http://deepface-api:5001/embedding
```

(nombre del servicio Docker, NO localhost)

## Comandos útiles

```bash
make logs          # Ver todos los logs
make logs-deepface # Solo DeepFace
make test-deepface # Verificar que la API responde
make restart       # Reiniciar servicios
make clean         # Eliminar todo (incluye volúmenes)
```

## Puertos expuestos

| Servicio | Puerto | Uso                           |
| -------- | ------ | ----------------------------- |
| n8n      | 5678   | UI del workflow               |
| DeepFace | 5001   | API de reconocimiento         |
| MQTT TCP | 1883   | OpenCV publisher conecta aquí |
| MQTT WS  | 9001   | WebSocket                     |
