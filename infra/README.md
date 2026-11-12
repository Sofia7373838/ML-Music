# `infra/` — infraestructura en AWS

La infraestructura está como código en dos plantillas de CloudFormation, para poder crearla,
revisarla y borrarla completa con la CLI de AWS.

| Plantilla | Stack | Recursos |
| --- | --- | --- |
| `base.yaml` | `music-recommender-base` | Bucket S3 versionado (datos y modelos), repositorio ECR, proveedor OIDC de GitHub, rol de GitHub Actions y presupuesto de AWS Budgets |
| `app.yaml` | `music-recommender-app` | Lambda (imagen de ECR), HTTP API de API Gateway, grupo de logs, dashboard, alarmas y tema SNS |

Son dos porque Lambda necesita que la imagen ya exista en ECR al crearse: primero se crea el
repositorio (`base`), se sube la imagen y luego se crea la función (`app`).

## Servicios y para qué se usan

| Servicio | Uso |
| --- | --- |
| S3 | `data/raw`, `data/processed` y `models/`. Versionado activado; versiones viejas se borran a los 90 días |
| SageMaker AI | Notebooks de exploración y entrenamiento (instancia pequeña, se apaga al terminar) |
| ECR | Imagen Docker de la API. Escaneo de vulnerabilidades al subir; se conservan las últimas 10 |
| Lambda | Ejecuta la API (FastAPI + Mangum) con 2048 MB y 30 s de tiempo máximo |
| API Gateway | HTTP API con una ruta `$default` que manda todo a la Lambda |
| CloudWatch | Logs (14 días), métricas EMF de la API, dashboard y alarmas |
| SNS | Manda las alarmas por correo |
| IAM | Rol de Lambda que solo puede leer el modelo; rol de GitHub Actions que solo puede subir a este ECR y actualizar esta función, y solo desde `main` |
| Budgets | Correo al 80 % del gasto real y al 100 % del pronosticado |

## Desplegar por primera vez

Requiere la [CLI de AWS](https://docs.aws.amazon.com/cli/) configurada y Docker. Los comandos
son para bash (en Windows: Git Bash o WSL). Cambia la región si usas otra.

```bash
export AWS_REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**1. Recursos base.** Usa `CreateOIDCProvider=false` si la cuenta ya tiene el proveedor
`token.actions.githubusercontent.com` (solo puede haber uno por cuenta).

```bash
aws cloudformation deploy --stack-name music-recommender-base \
  --template-file infra/base.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides GitHubRepo=<owner>/<repo> BudgetEmail=<correo> BudgetLimitUSD=10

aws cloudformation describe-stacks --stack-name music-recommender-base \
  --query "Stacks[0].Outputs" --output table
```

**2. Subir datos y modelo** (después de entrenar, ver [`models/README.md`](../models/README.md)):

```bash
export BUCKET=music-recommender-$ACCOUNT_ID
aws s3 cp data/raw/dataset.csv s3://$BUCKET/data/raw/dataset.csv
aws s3 cp models/recommender.joblib s3://$BUCKET/models/recommender.joblib
```

**3. Primera imagen.**

```bash
export REPO=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/music-recommender
aws ecr get-login-password | docker login --username AWS --password-stdin ${REPO%%/*}
docker build --platform linux/amd64 --provenance=false -t $REPO:v1 .
docker push $REPO:v1
```

`--provenance=false` es necesario: Lambda no acepta los manifiestos multiplataforma que
Docker Buildx genera por omisión.

**4. API.**

```bash
aws cloudformation deploy --stack-name music-recommender-app \
  --template-file infra/app.yaml --capabilities CAPABILITY_IAM \
  --parameter-overrides ImageUri=$REPO:v1 ArtifactsBucket=$BUCKET AlarmEmail=<correo>

export API_URL=$(aws cloudformation describe-stacks --stack-name music-recommender-app \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
curl $API_URL/health
```

Confirma la suscripción que llega por correo para recibir las alarmas.

**5. CD.** En GitHub, *Settings → Secrets and variables → Actions → Variables*, crea estas
variables del repositorio (no son secretos: no hay llaves de acceso):

| Variable | Valor |
| --- | --- |
| `AWS_REGION` | `us-east-1` |
| `AWS_ROLE_ARN` | Salida `GitHubActionsRoleArn` del stack base |
| `ECR_REPOSITORY` | `music-recommender` |
| `LAMBDA_FUNCTION` | `music-recommender-api` |
| `API_URL` | Salida `ApiUrl` del stack app (para la prueba de humo) |

Desde ese momento cada merge a `main` que pase el CI se despliega solo (ver
[`.github/workflows/README.md`](../.github/workflows/README.md)).

## Monitoreo

`app.yaml` crea:

- **Dashboard `music-recommender`**: invocaciones, errores y throttles de Lambda; latencia
  p50/p95 del modelo; canciones no encontradas; duración de Lambda; y una tabla con las
  últimas 50 predicciones (CloudWatch Logs Insights).
- **Alarma `music-recommender-errores`**: al menos un error de Lambda en 5 minutos.
- **Alarma `music-recommender-latencia`**: p95 de `Latency` arriba de `LatencyAlarmMs`
  (500 ms) durante 15 minutos.

Las dos avisan al tema SNS `music-recommender-alarmas`. La URL del dashboard queda en la salida
`DashboardUrl`. Las métricas personalizadas las genera la API, ver
[`api/README.md`](../api/README.md#monitoreo).

## AWS Academy (Learner Lab)

Las cuentas de Learner Lab no permiten crear roles de IAM, proveedores OIDC ni presupuestos.
En ese caso:

- No despliegues `base.yaml` tal cual: crea el bucket y el repositorio ECR desde la consola o
  la CLI (`aws s3 mb`, `aws ecr create-repository`).
- Despliega `app.yaml` con `LambdaRoleArn=arn:aws:iam::<cuenta>:role/LabRole`.
- El CD por OIDC no funcionará; despliega con los pasos 3 y 4 (o con
  `aws lambda update-function-code`) desde tu máquina.

## Costos y limpieza

Con poco tráfico todo queda dentro de la capa gratuita o en centavos: Lambda y API Gateway
cobran por petición, S3 guarda ~30 MB y ECR unos cientos de MB. Lo que más cuesta es dejar
prendida la instancia de SageMaker.

Para borrar todo:

```bash
aws cloudformation delete-stack --stack-name music-recommender-app
aws ecr delete-repository --repository-name music-recommender --force
aws cloudformation delete-stack --stack-name music-recommender-base
```

El bucket tiene `DeletionPolicy: Retain` para no perder datos por accidente; bórralo a mano
(vacía todas las versiones antes) si ya no lo necesitas.
