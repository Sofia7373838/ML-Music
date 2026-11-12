# `api/` — API de inferencia

API REST hecha con FastAPI. En AWS corre dentro de Lambda (adaptador Mangum) detrás de una
HTTP API de API Gateway; en local corre con uvicorn.

| Archivo | Qué hace |
| --- | --- |
| `main.py` | La aplicación FastAPI y sus endpoints |
| `model_store.py` | Carga el modelo una sola vez por contenedor, desde S3 o desde disco |
| `monitoring.py` | Escribe un log estructurado por predicción (CloudWatch EMF) |
| `handler.py` | Punto de entrada de Lambda (`api.handler.handler`) |

## Endpoints

La documentación interactiva queda en `/docs` (Swagger) y `/redoc`.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| `GET` | `/health` | Estado, modelo cargado, número de canciones y fecha de entrenamiento |
| `GET` | `/songs/search?q=<texto>&limit=10` | Busca por nombre o artista; las más populares primero |
| `GET` | `/songs/{track_id}` | Datos de una canción |
| `POST` | `/recommendations` | Recibe una canción y devuelve las `k` más parecidas |

Cuerpo de `POST /recommendations`:

| Campo | Tipo | Por omisión | Qué es |
| --- | --- | --- | --- |
| `track_id` | texto | (obligatorio) | Canción de entrada; se obtiene con `/songs/search` |
| `k` | 1 a 50 | 10 | Número de recomendaciones |
| `max_popularity` | 0 a 100 | `null` | Solo recomendar canciones con esa popularidad o menos, para descubrir artistas con poca visibilidad |

Respuestas de error: `404` si la canción no existe y `422` si el cuerpo no es válido.

### Ejemplo

```bash
curl "http://localhost:8000/songs/search?q=bohemian%20rhapsody&limit=1"

curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"track_id": "4u7EnebtmKWzUH433cf5Qv", "k": 3}'
```

```json
{
  "model": "cluster_knn",
  "query": {"track_id": "4u7EnebtmKWzUH433cf5Qv", "track_name": "Bohemian Rhapsody - Remastered 2011", "artists": "Queen", "...": "..."},
  "recommendations": [
    {"track_name": "Will o the Wisp", "artists": "Opeth", "track_genre": "death-metal", "popularity": 44, "similarity": 0.9348, "...": "..."},
    {"track_name": "Melt My Heart To Stone", "artists": "Adele", "track_genre": "british", "popularity": 52, "similarity": 0.9346, "...": "..."},
    {"track_name": "Le trou noir", "artists": "Stupeflip;MC Salo", "track_genre": "french", "popularity": 32, "similarity": 0.9345, "...": "..."}
  ]
}
```

`similarity` es la similitud coseno (de -1 a 1) entre la canción de entrada y la recomendada
en el espacio de características estandarizadas.

## Correr en local

Requiere `models/recommender.joblib` (ver [`src/recommender/README.md`](../src/recommender/README.md#entrenar)).
Desde la raíz del repositorio:

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

En PowerShell:

```powershell
$env:PYTHONPATH = "src"
uvicorn api.main:app --reload
```

### Probar la imagen de Lambda en local

La imagen base de Lambda trae el emulador de la API de Lambda. Se monta el modelo local en
vez de descargarlo de S3:

```bash
docker build --platform linux/amd64 --provenance=false -t music-recommender .
docker run --rm -p 9000:8080 \
  -v "$(pwd)/models:/models" -e MODEL_PATH=/models/recommender.joblib \
  music-recommender

curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations -d '{
  "version": "2.0", "routeKey": "$default", "rawPath": "/health", "rawQueryString": "",
  "headers": {"host": "localhost"},
  "requestContext": {
    "http": {"method": "GET", "path": "/health", "sourceIp": "127.0.0.1", "protocol": "HTTP/1.1"},
    "stage": "$default", "requestId": "local"
  },
  "isBase64Encoded": false
}'
```

## Carga del modelo

| Variable | Cuándo se usa |
| --- | --- |
| `MODEL_S3_URI` | En Lambda: `s3://<bucket>/models/recommender.joblib`. Se descarga a `/tmp` |
| `MODEL_PATH` | Si no hay `MODEL_S3_URI`. Por omisión `models/recommender.joblib` |

`handler.py` carga el modelo al importarse, es decir, en la fase de inicio de Lambda. Así
solo el arranque en frío paga la descarga y la deserialización (unos segundos); las demás
peticiones del mismo contenedor reutilizan el modelo en memoria.

## Monitoreo

Cada llamada a `/recommendations` escribe en stdout una línea JSON con formato
[CloudWatch Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html).
CloudWatch Logs la guarda como log y además crea estas métricas en el namespace
`MusicRecommender` (dimensión `Endpoint`), sin llamadas extra a la API de CloudWatch:

| Métrica | Unidad | Qué es |
| --- | --- | --- |
| `Latency` | ms | Tiempo de buscar la canción y generar las recomendaciones |
| `Recommendations` | conteo | Cuántas canciones se regresaron |
| `SongNotFound` | conteo | 1 si el `track_id` no existe |

Además el log incluye `model`, `track_id`, `k` y `max_popularity`. **No se registra ningún
dato personal** (ni IP, ni usuario, ni encabezados): solo la canción consultada, el resultado
y el tiempo de respuesta. El dashboard y las alarmas que usan estas métricas están en
[`infra/app.yaml`](../infra/app.yaml).
