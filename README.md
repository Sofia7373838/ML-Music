# Sistema de recomendación de música
Materia: Integración de Servicios de Aprendizaje Automático

Equipo: Sofía Vanessa Noyola Fonseca y Néstor Eduardo Pérez Avalos

Profesor: Dr. Miguel Ángel Alejandro Islas Toski

Recomendador basado en contenido: dada una canción, regresa las más parecidas según sus
características de audio. Se consume con una API REST desplegada en AWS.

## Modelos
| Modelo | Descripción |
| --- | --- |
| A (`knn`) | kNN con similitud coseno sobre todo el catálogo |
| B (`cluster_knn`) | K-Means (K = 8) + kNN dentro del clúster de la canción |
| Referencia (`random`) | Recomendaciones al azar |

Ningún modelo recibe el género como variable, porque el género se usa para evaluar.
Las columnas de cada grupo están en [`src/recommender/config.py`](src/recommender/config.py).

### Resultados

81,061 canciones, 2,000 canciones de prueba, k = 10
([`models/metrics.json`](models/metrics.json)):

| Modelo | Precision@10 | Diversidad | Artistas distintos | Sesgo de popularidad | Cobertura | Latencia p95 |
| --- | --- | --- | --- | --- | --- | --- |
| A `knn` | 0.317 | 0.053 | 9.65 | -0.37 | 21.5 % | 10.2 ms |
| **B `cluster_knn`** | **0.316** | 0.053 | 9.65 | -0.39 | 21.5 % | **2.1 ms** |
| Referencia `random` | 0.122 | 0.935 | 9.99 | -0.63 | 21.9 % | 0.1 ms |

**Modelo elegido: B.** Los dos modelos recomiendan el mismo macro-género 2.6 veces más que
el azar. B pierde menos de 0.001 de precisión frente a A y es unas 5 veces más rápido, así que
gana por la regla de desempate (ver [`src/recommender/README.md`](src/recommender/README.md#elección-del-modelo-final)).
La latencia depende de la máquina; las proporciones se mantienen.

### Mitigaciones del análisis ético en el código

Las medidas de la sección 9.4 del avance 1 que se pueden programar ya están implementadas:

| # | Medida | Dónde |
| --- | --- | --- |
| 1 | Evaluar por macro-género, no solo en promedio | `metrics.by_group` → `by_macro_genre` en `models/metrics.json`; sección 5 de `02_modelos.ipynb` |
| 3 | Máximo 2 canciones por artista en cada lista | `max_per_artist` (por omisión 2) en `POST /recommendations` |
| 4 | Modo descubrimiento | `max_popularity` en `POST /recommendations` |
| 5 | Filtro de contenido explícito | `exclude_explicit` en `POST /recommendations` |
| 6 | Limpieza de duplicados | `recommender.data.clean` |
| 7 | Monitorear popularidad y *hubs* | Métricas `RecommendedPopularity` y `ExplicitRecommended`, y tablas de Logs Insights en el dashboard |
| 8 | Transparencia | Campo `reason` en cada recomendación ("Comparten: mucha energía y tempo rápido") y la ficha del modelo de abajo |

## Arquitectura
SageMaker entrena, S3 guarda los datos y el modelo, y Lambda lo sirve detrás de API Gateway.
La imagen de la API vive en ECR y CloudWatch recibe los logs y las métricas.

```text
GitHub Actions ──(OIDC)──> ECR ──> Lambda (FastAPI + Mangum) <── API Gateway (HTTP) <── cliente
                                     │  ▲
                        logs EMF     │  └── modelo: s3://<bucket>/models/recommender.joblib
                                     ▼
                                CloudWatch (dashboard + alarmas) ──> SNS (correo)
```

Toda la infraestructura está como código en Terraform (`infra/`): un `terraform apply` la crea
completa, sube el modelo y despliega la API. Para replicar el proyecto en otra cuenta solo
hacen falta credenciales de AWS (ver [`infra/README.md`](infra/README.md)).

## Estructura

Cada carpeta tiene su propio README con el detalle de esa sección.

```text
.github/workflows/   CI (ruff, pytest, build de Docker) y CD a AWS      → README
api/                 API de inferencia (FastAPI) y logs de monitoreo    → README
data/                Dataset original y limpio (no se suben a Git)      → README
infra/               Infraestructura en AWS con Terraform               → README
models/              Artefacto entrenado y reporte de métricas          → README
notebooks/           Análisis exploratorio y comparación de modelos     → README
src/recommender/     Carga, preprocesamiento, modelos y entrenamiento   → README
tests/               Pruebas unitarias y validación de datos            → README
Dockerfile           Imagen de la API para AWS Lambda
```

## Preparar el entorno

Requiere Python 3.13.

En Windows (PowerShell):

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

En macOS o Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

| Archivo | Para qué |
| --- | --- |
| `requirements.txt` | Lo necesario para entrenar y cargar el modelo |
| `requirements-api.txt` | Lo anterior más FastAPI, Mangum y boto3 (lo que lleva la imagen de Lambda) |
| `requirements-dev.txt` | Todo lo anterior más notebooks, pruebas, linter y servidor local |

## Uso rápido

```bash
# 1. Datos: descarga dataset.csv de Kaggle en data/raw/ y corre notebooks/01_exploracion_datos.ipynb
# 2. Entrenar, evaluar y guardar el mejor modelo en models/
PYTHONPATH=src python -m recommender.train
# 3. Levantar la API en http://localhost:8000/docs
PYTHONPATH=src uvicorn api.main:app --reload
```

En PowerShell, en vez de `PYTHONPATH=src ...` usa `$env:PYTHONPATH = "src"` antes del comando.

## Antes de subir cambios

Son las mismas revisiones que corre el CI:

```bash
ruff check .
ruff format --check .
pytest
```

## Datos

Se usa el [Spotify Tracks Dataset](https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset)
con fines exclusivamente académicos. Los datos se obtuvieron de la API de Spotify, por lo que
no se redistribuyen en este repositorio. Detalles en [`data/README.md`](data/README.md).

## Ficha del modelo (model card)

| | |
| --- | --- |
| **Qué hace** | Dada una canción del catálogo, regresa las k más parecidas por sus características de audio |
| **Modelo** | K-Means (K = 8) + kNN con similitud coseno dentro del clúster (`cluster_knn`) |
| **Entrada** | 10 variables de audio de Spotify: 9 estandarizadas y `mode` |
| **No usa** | Género, popularidad, artista, idioma, país ni ningún dato de usuarios |
| **Datos** | Spotify Tracks Dataset (Kaggle), 81,061 canciones únicas de 114 géneros después de limpiar |
| **Evaluación** | Precision@10 de macro-género 0.316 (azar: 0.122), con métricas por macro-género en `models/metrics.json` |
| **Uso previsto** | Proyecto académico: descubrir canciones parecidas a una que ya te gusta |
| **Fuera de alcance** | Uso comercial (las políticas de Spotify no permiten entrenar modelos con sus datos), canciones fuera del catálogo, recomendaciones personalizadas por usuario |

### Limitaciones conocidas

- **Representación**: el catálogo está cargado hacia música occidental y en inglés; los géneros
  con pocas canciones tienen menos vecinos buenos. Revisa `by_macro_genre` antes de confiar en
  el promedio.
- **Las características son una caja negra de Spotify**: dos canciones con números parecidos
  pueden sonar distinto para una persona. La similitud es aproximada.
- **Burbuja de filtro**: el modelo regresa lo más parecido, así que la diversidad de las listas
  es baja (0.05 contra 0.94 del azar). El tope por artista y el modo descubrimiento la mitigan
  en parte.
- **Hubs**: algunas canciones quedan cerca de muchas otras y salen en muchas listas. Se mide con
  `max_appearances` al evaluar y con el dashboard en producción.
- **Versiones de la misma canción** con nombre distinto (por ejemplo "Remastered 2011") no se
  detectan como duplicados.
- **Precision@k de género no es la meta**: optimizarla sola premiaría la burbuja. Por eso se
  reporta junto con diversidad, cobertura y sesgo de popularidad.

### Privacidad

La API no pide ni guarda datos de usuarios. El log de cada predicción contiene solo la canción
consultada, las recomendadas, los filtros y la latencia (hay una prueba que lo garantiza en
`tests/test_monitoring.py`).

## Avance

- [x] Definición del proyecto
- [x] Repositorio y CI
- [x] Datos
- [x] Modelos
- [x] Código modular
- [x] Pruebas
- [x] API de inferencia
- [x] Mitigaciones del análisis ético en el código (filtros, tope por artista, explicación, métricas por género)
- [x] Infraestructura en AWS (desplegada con Terraform en `us-east-1`, con un usuario de IAM de permisos mínimos)
- [x] Interfaz web (`api/static/index.html`, servida en `/` desde la misma API)
- [x] Monitoreo (dashboard y alarmas de `infra/monitoring.tf` desplegados)
- [ ] CD (workflow y rol OIDC listos, falta crear en GitHub las variables de `terraform output github_variables`)
- [ ] Documentación: reporte PDF y póster (borradores fuera del repositorio, falta agregar resultados y capturas de AWS)
