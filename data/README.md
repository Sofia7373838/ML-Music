# `data/` — datasets

Ninguno de los CSV se sube a Git (`.gitignore`); solo se versionan las carpetas vacías.

| Ruta | Qué es | Cómo se obtiene |
| --- | --- | --- |
| `raw/dataset.csv` | Spotify Tracks Dataset original (114,000 filas, ~20 MB) | Descarga manual de Kaggle |
| `processed/tracks_clean.csv` | Una fila por canción, con `macro_genre` (81,061 filas) | `notebooks/01_exploracion_datos.ipynb` |

## Descargar el dataset

1. Entra a <https://www.kaggle.com/datasets/maharshipandya/-spotify-tracks-dataset>.
2. Descarga y descomprime `dataset.csv` en `data/raw/`.

Para compartirlo con el equipo y con SageMaker, súbelo al bucket del proyecto (lo crea
`infra/base.yaml`; el bucket tiene versionado):

```bash
aws s3 cp data/raw/dataset.csv s3://<bucket>/data/raw/dataset.csv
aws s3 cp data/processed/tracks_clean.csv s3://<bucket>/data/processed/tracks_clean.csv
```

## Limpieza (`recommender.data.clean`)

1. Se quedan solo las columnas que usa el proyecto.
2. Se quitan filas con nulos.
3. Se quitan filas con `tempo` = 0 (no se detectó ritmo: ruido blanco, audio para dormir).
4. Se agrega `macro_genre` a partir de `track_genre` (`recommender.genres`).
5. Duplicados: la misma canción aparece con varios `track_id` o en varios géneros. Queda una
   fila por nombre + artistas (sin distinguir mayúsculas), la más popular, y su macro-género
   es el más frecuente entre todas sus apariciones.

## Validación (`recommender.data.validate`)

Se corre antes de cada entrenamiento y reporta todos los problemas a la vez:

- Que estén todas las columnas, incluida `macro_genre`.
- Que no haya nulos ni `track_id` repetidos, y que el dataset no esté vacío.
- Rangos válidos:

| Columnas | Rango |
| --- | --- |
| `danceability`, `energy`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `valence` | 0 a 1 |
| `loudness` | -60 a 5 dB |
| `tempo` | 1 a 300 BPM |
| `mode` | 0 o 1 |
| `popularity` | 0 a 100 |

## Uso de los datos

Los datos se obtuvieron de la API de Spotify y sus políticas para desarrolladores no permiten
usar su contenido para entrenar modelos de ML. Este proyecto los usa solo con fines académicos,
sin fines de lucro y sin publicarlo como producto, y por eso no se redistribuyen aquí.
