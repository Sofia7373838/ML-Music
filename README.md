# Sistema de recomendación de música
Materia: Integración de Servicios de Aprendizaje Automático
Equipo: Sofía Vanessa Noyola Fonseca y Néstor Eduardo Pérez Avalos
Profesor: 

Recomendador basado en contenido: dada una canción, regresa las más parecidas según sus
características de audio. Se consume con una API REST desplegada en AWS.


## Modelos
| Modelo | Descripción |
| --- | --- |
| A | kNN con similitud coseno sobre todo el catálogo |
| B | K-Means + kNN dentro del clúster de la canción |
| Referencia | Recomendaciones al azar |

Ningún modelo recibe el género como variable, porque el género se usa para evaluar.
Las columnas de cada grupo están en [`src/recommender/config.py`](src/recommender/config.py).

## Arquitectura
SageMaker entrena, S3 guarda los datos y el modelo, y Lambda lo sirve detrás de API Gateway.
La imagen de la API vive en ECR y CloudWatch recibe los logs y las métricas.

## Estructura

```text
.github/workflows/   CI con ruff y pytest
api/                 API de inferencia
data/raw/            Dataset original (no se sube a Git)
data/processed/      Dataset limpio (no se sube a Git)
notebooks/           Análisis exploratorio y experimentos
src/recommender/     Carga, preprocesamiento y recomendador
tests/               Pruebas unitarias y validación de datos
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
no se redistribuyen en este repositorio. Para trabajar en local, descarga `dataset.csv` en `data/raw/`.

## Avance

- [x] Definición del proyecto
- [x] Repositorio y CI
- [ ] Datos
- [ ] Modelos
- [ ] Código modular
- [ ] Pruebas
- [ ] API de inferencia
- [ ] Infraestructura en AWS
- [ ] CD
- [ ] Monitoreo
- [ ] Documentación