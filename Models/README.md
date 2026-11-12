# `models/` — artefactos del modelo

`python -m recommender.train` escribe aquí dos archivos:

| Archivo | ¿En Git? | Qué es |
| --- | --- | --- |
| `recommender.joblib` | No (`*.joblib` en `.gitignore`), ~10 MB | `SongRecommender` completo: preprocesador ajustado, modelo entrenado y catálogo de canciones |
| `metrics.json` | Sí | Fecha, número de canciones, modelo elegido, K, semilla, versiones de las librerías y las métricas de los tres modelos |

`metrics.json` sí se sube para dejar registro de qué modelo se eligió y por qué. El artefacto
se versiona en S3, no en Git.

## Publicar una versión del modelo

```bash
aws s3 cp models/recommender.joblib s3://<bucket>/models/recommender.joblib
aws s3 cp models/metrics.json s3://<bucket>/models/metrics.json
```

El bucket tiene versionado: cada `cp` crea una versión nueva y las anteriores se conservan 90
días. La Lambda carga el modelo al arrancar, así que para que tome la versión nueva hay que
forzar contenedores nuevos (por ejemplo, volver a desplegar o cambiar cualquier variable de
entorno):

```bash
aws lambda update-function-configuration --function-name music-recommender-api \
  --description "modelo $(date +%Y-%m-%d)"
```

Para regresar a una versión anterior:

```bash
aws s3api list-object-versions --bucket <bucket> --prefix models/recommender.joblib
aws s3api copy-object --bucket <bucket> --key models/recommender.joblib \
  --copy-source "<bucket>/models/recommender.joblib?versionId=<id>"
```

## Compatibilidad

joblib guarda objetos de scikit-learn con pickle, así que el artefacto **solo se puede cargar
con las mismas versiones** con las que se entrenó (están en `metrics.json`). Por eso las
versiones de `requirements.txt` están fijadas y la imagen de Lambda usa ese mismo archivo. Si
se actualiza scikit-learn, numpy o pandas, hay que reentrenar y volver a subir el artefacto.

Solo carga artefactos que generó el equipo: abrir un pickle ejecuta código.
