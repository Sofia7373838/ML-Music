"""Punto de entrada de AWS Lambda (CMD del Dockerfile: `api.handler.handler`)."""

from mangum import Mangum

from api.main import app
from api.model_store import get_recommender

# Cargar el modelo al importar el módulo hace que ocurra en la fase de inicio de Lambda
# (una vez por contenedor) y no en la primera petición.
get_recommender()

# lifespan="off": Mangum correría el ciclo de vida en cada invocación.
handler = Mangum(app, lifespan="off")
