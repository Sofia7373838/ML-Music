# `models/` — artefactos del modelo

`python -m recommender.train` escribe aquí dos archivos:

| Archivo | ¿En Git? | Qué es |
| --- | --- | --- |
| `recommender.joblib` | No (`*.joblib` en `.gitignore`), ~10 MB | `SongRecommender` completo: preprocesador ajustado, modelo entrenado y catálogo de canciones |
| `metrics.json` | No (`.gitignore`) | Fecha, número de canciones, modelo elegido, K, semilla, versiones de las librerías y las métricas de los tres modelos |

Los dos se versionan en S3, no en Git: Terraform los sube al bucket del proyecto junto con
cada versión del modelo, así queda registro de qué modelo se eligió y con qué métricas.

## Publicar una versión del modelo

Después de reentrenar, desde `infra/`:

```bash
terraform apply
```

Terraform detecta que `recommender.joblib` cambió (compara su huella MD5), lo sube a S3 y
actualiza la variable `MODEL_VERSION` de la Lambda. La Lambda carga el modelo una sola vez
por contenedor; al cambiar esa variable, AWS arranca contenedores nuevos que cargan la versión
nueva. El bucket tiene versionado: las versiones anteriores se conservan 90 días.

Para regresar a una versión anterior:

```bash
aws s3api list-object-versions --bucket <bucket> --prefix models/recommender.joblib
aws s3api copy-object --bucket <bucket> --key models/recommender.joblib \
  --copy-source "<bucket>/models/recommender.joblib?versionId=<id>"
```

Ojo: el siguiente `terraform apply` vuelve a subir el modelo de tu carpeta `models/`. Para
que el regreso sea permanente, reentrena con la versión de código anterior o reemplaza tu
archivo local por el de esa versión.

## Compatibilidad

joblib guarda objetos de scikit-learn con pickle, así que el artefacto **solo se puede cargar
con las mismas versiones** con las que se entrenó (están en `metrics.json`). Por eso las
versiones de `requirements.txt` están fijadas y la imagen de Lambda usa ese mismo archivo. Si
se actualiza scikit-learn, numpy o pandas, hay que reentrenar y volver a subir el artefacto.

Solo carga artefactos que generó el equipo: abrir un pickle ejecuta código.
