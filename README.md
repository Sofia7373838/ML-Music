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

## Estructura

Cada carpeta tiene su propio README con el detalle de esa sección.

```text
.github/workflows/   CI (ruff, pytest, build de Docker) y CD a AWS      → README
api/                 API de inferencia (FastAPI) y logs de monitoreo    → README
data/                Dataset original y limpio (no se suben a Git)      → README
infra/               Plantillas de CloudFormation para AWS              → README
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

## Avance

- [x] Definición del proyecto
- [x] Repositorio y CI
- [x] Datos
- [x] Modelos
- [x] Código modular
- [x] Pruebas
- [x] API de inferencia
- [ ] Infraestructura en AWS (plantillas listas en `infra/`, falta desplegar)
- [ ] CD (workflow listo, falta configurar las variables del repositorio)
- [ ] Monitoreo (dashboard y alarmas en `infra/app.yaml`, falta desplegar)
- [ ] Documentación (análisis ético y social, reporte PDF, póster)
