.PHONY: up down build logs restart clean

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache deepface-api

logs:
	docker compose logs -f

logs-deepface:
	docker compose logs -f deepface-api

logs-n8n:
	docker compose logs -f n8n

restart:
	docker compose restart

clean:
	docker compose down -v --remove-orphans

status:
	docker compose ps

# Probar que DeepFace responde
test-deepface:
	curl -s http://localhost:5001/health | python3 -m json.tool
