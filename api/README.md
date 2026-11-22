# `api/` — API de inferencia

API REST hecha con FastAPI. En AWS corre dentro de Lambda (adaptador Mangum) detrás de una
HTTP API de API Gateway; en local corre con uvicorn.

| Archivo | Qué hace |
| --- | --- |
| `main.py` | La aplicación FastAPI y sus endpoints |
| `model_store.py` | Carga el modelo una sola vez por contenedor, desde S3 o desde disco |
| `monitoring.py` | Escribe un log estructurado por predicción (CloudWatch EMF) |
| `handler.py` | Punto de entrada de Lambda (`api.handler.handler`) |
| `static/index.html` | Interfaz web (HTML, CSS y JavaScript sin librerías) que se sirve en `/` |

## Interfaz web

Al abrir la raíz de la API (`http://localhost:8000/` en local, o la `api_url` de Terraform en
AWS) aparece una página para usar el recomendador sin escribir peticiones a mano:

- **Buscador** con sugerencias mientras escribes (consulta `/songs/search` 300 ms después de
  la última tecla) y navegación con flechas, Enter y Esc.
- **Ajustes** con los filtros del análisis ético: número de recomendaciones, modo
  descubrimiento (`max_popularity`), excluir contenido explícito y máximo por artista. Al
  cambiar uno, la lista se vuelve a pedir sola.
- **Resultados**: la canción base, un resumen (similitud y popularidad promedio, géneros y
  artistas distintos, explícitas) y cada recomendación con su explicación (`reason`), barras de
  similitud y popularidad, y botones para **usarla como base** o abrirla en Spotify.
- **Estados**: aviso de arranque en frío si la API tarda, mensajes claros para 404, 422 y
  errores de red, y estado del modelo en el encabezado (`/health`).
- **Enlace compartible**: la URL guarda la canción (`/#track=<track_id>`); al abrirla se
  cargan sus recomendaciones.

Decisiones de diseño:

- **Se sirve desde la misma API**, no desde S3 u otro servicio: no hace falta CORS ni
  infraestructura nueva, y se despliega junto con la imagen de Docker.
- **Rutas relativas** (`health`, `songs/search`, `recommendations`) calculadas a partir de
  la URL de la página: funciona en `localhost` y en cualquier etapa de API Gateway.
- **Sin dependencias**: un solo archivo, sin React ni Node, sin pasos de compilación.
- Todo el texto que llega de la API se inserta con `textContent`, nunca como HTML, para que
  un nombre de canción no pueda inyectar código en la página.
- Las portadas son degradados generados: el color base depende del género, así se ve de un
  vistazo qué tan variada es la lista.

La ruta `/` no aparece en `/docs` (`include_in_schema=False`) y no carga el modelo: la página
abre aunque la Lambda todavía lo esté descargando.

Si agregas archivos a `static/`, ya quedan incluidos en la imagen (`.dockerignore` permite
`api/static/*`) y en la huella con la que Terraform decide reconstruirla.

## Endpoints

La documentación interactiva queda en `/docs` (Swagger) y `/redoc`.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| `GET` | `/` | Interfaz web (ver arriba) |
| `GET` | `/health` | Estado, modelo cargado, número de canciones y fecha de entrenamiento |
| `GET` | `/songs/search?q=<texto>&limit=10` | Busca por nombre o artista; las más populares primero |
| `GET` | `/songs/{track_id}` | Datos de una canción |
| `POST` | `/recommendations` | Recibe una canción y devuelve las `k` más parecidas |

Cuerpo de `POST /recommendations`:

| Campo | Tipo | Por omisión | Qué es |
| --- | --- | --- | --- |
| `track_id` | texto | (obligatorio) | Canción de entrada; se obtiene con `/songs/search` |
| `k` | 1 a 50 | 10 | Número de recomendaciones |
| `max_popularity` | 0 a 100 | `null` | Modo descubrimiento: solo recomendar canciones con esa popularidad o menos, para dar visibilidad a artistas pequeños |
| `exclude_explicit` | booleano | `false` | Quitar canciones con contenido explícito |
| `max_per_artist` | 1 a 50 o `null` | 2 | Máximo de canciones de un mismo artista en la lista; `null` = sin tope |

Cada canción de la respuesta trae `explicit`, y cada recomendación además `similarity` y
`reason` (qué rasgos de audio comparte con la de entrada). Estos parámetros son las
mitigaciones 3, 4, 5 y 8 del análisis ético.

Respuestas de error: `404` si la canción no existe y `422` si el cuerpo no es válido.

### Ejemplo

```bash
curl "http://localhost:8000/songs/search?q=bohemian%20rhapsody&limit=1"

curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"track_id": "4u7EnebtmKWzUH433cf5Qv", "k": 3}'

# Sin explícitas, solo canciones poco populares
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"track_id": "4u7EnebtmKWzUH433cf5Qv", "k": 5, "exclude_explicit": true, "max_popularity": 30}'
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

Con esta versión cada recomendación también trae `"explicit": false` y un campo como
`"reason": "Comparten: volumen alto y tempo rápido"`. Los valores exactos dependen del modelo
entrenado.

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
| `RecommendedPopularity` | valor | Popularidad de cada canción recomendada (lista de valores; CloudWatch calcula promedio y percentiles). Vigila el sesgo de popularidad |
| `ExplicitRecommended` | conteo | Cuántas canciones explícitas se regresaron |

Además el log incluye `model`, `track_id`, `k`, los filtros (`max_popularity`,
`exclude_explicit`, `max_per_artist`) y `recommended_ids`, que el dashboard usa para detectar
*hubs* (canciones que salen en demasiadas listas). **No se registra ningún dato personal** (ni
IP, ni usuario, ni encabezados): solo canciones, filtros, el resultado y el tiempo de respuesta. El dashboard y las alarmas que usan estas métricas están en
[`infra/monitoring.tf`](../infra/monitoring.tf).
