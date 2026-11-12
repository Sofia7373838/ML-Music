# Imagen de la API para AWS Lambda. Construir desde la raíz del repositorio:
#   docker build --platform linux/amd64 --provenance=false -t music-recommender .
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt requirements-api.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements-api.txt

# El paquete `recommender` debe ser importable para cargar el artefacto con joblib.
COPY src/recommender ${LAMBDA_TASK_ROOT}/recommender
COPY api ${LAMBDA_TASK_ROOT}/api

# El modelo no va en la imagen: se descarga de S3 al iniciar (variable MODEL_S3_URI).
CMD ["api.handler.handler"]
