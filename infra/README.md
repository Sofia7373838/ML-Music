# `infra/` — infraestructura en AWS con Terraform

Toda la infraestructura está como código en Terraform. Un solo `terraform apply` crea los
servicios de AWS, sube el modelo a S3, construye la imagen de Docker y despliega la API.
Para replicar el proyecto en otra cuenta solo hacen falta credenciales de AWS.

## Qué crea

| Archivo | Servicio | Qué crea |
| --- | --- | --- |
| `storage.tf` | S3 | Bucket versionado y cifrado, sin acceso público. Sube `models/recommender.joblib` y, si existen, `dataset.csv`, `tracks_clean.csv` y `metrics.json` |
| `ecr.tf` | ECR | Repositorio de la imagen (escaneo al subir, se conservan las últimas 10). Construye y sube la imagen con Docker |
| `lambda.tf` | Lambda + IAM | La función que ejecuta la API (2048 MB, 30 s), su rol (solo puede leer el modelo) y su grupo de logs (14 días) |
| `api_gateway.tf` | API Gateway | HTTP API pública que manda todas las rutas a la Lambda |
| `monitoring.tf` | CloudWatch + SNS | Dashboard, alarma de errores, alarma de latencia y tema SNS para avisos por correo |
| `github.tf` | IAM | Proveedor OIDC y rol para el workflow de CD (solo si se define `github_repo`) |
| `budget.tf` | Budgets | Aviso al 80 % del gasto real y al 100 % del pronosticado (solo si hay correo) |

Los demás archivos:

| Archivo | Para qué |
| --- | --- |
| `versions.tf` | Versión de Terraform y del proveedor de AWS; etiqueta todos los recursos con `Project` |
| `variables.tf` | Lo que se puede ajustar, todo con valores por omisión |
| `main.tf` | Valores calculados (nombres, etiqueta de la imagen) |
| `outputs.tf` | Lo que imprime al terminar: URL de la API, dashboard y variables para GitHub |
| `terraform.tfvars.example` | Ejemplo de configuración; se copia como `terraform.tfvars` |
| `.terraform.lock.hcl` | Fija la versión exacta del proveedor para todo el equipo (sí va en Git) |

SageMaker AI no lo crea Terraform: se usa a mano para los notebooks y se apaga al terminar.

## Requisitos

- [Terraform](https://developer.hashicorp.com/terraform/install) 1.6 o más nuevo.
- [AWS CLI](https://docs.aws.amazon.com/cli/) con credenciales de un usuario de IAM, **no de
  root** (ver [Usuario de IAM para desplegar](#usuario-de-iam-para-desplegar)). En Learner Lab
  se usan las credenciales del laboratorio. Revisa con `aws sts get-caller-identity`.
- [Docker](https://docs.docker.com/get-docker/) **encendido**: Terraform lo usa para construir la imagen.
- El modelo entrenado en `models/recommender.joblib`
  (ver [`src/recommender/README.md`](../src/recommender/README.md#entrenar)).

## Usuario de IAM para desplegar

La cuenta root puede hacer todo, incluido cerrar la cuenta, y sus llaves no se pueden limitar.
AWS recomienda no usarla para el trabajo diario. Para desplegar se crea un usuario de IAM con
la política [`iam/deployer-policy.json`](iam/deployer-policy.json), que solo permite:

| Servicio | Qué permite |
| --- | --- |
| S3, ECR, Lambda | Todo, pero solo sobre recursos cuyo nombre empieza con `music-recommender` |
| API Gateway | Crear, cambiar y borrar HTTP APIs |
| IAM | Crear roles `music-recommender-*`, pasarlos **solo a Lambda**, adjuntarles **solo** la política básica de Lambda, y administrar el proveedor OIDC de GitHub |
| CloudWatch, SNS, Budgets | Logs, alarmas, dashboard, tema y presupuesto del proyecto, y leer métricas y logs |

No puede tocar otros buckets, funciones ni usuarios de la cuenta. Si cambias `project_name`,
cambia también `music-recommender` en la política.

Una sola vez, con la cuenta root en la [consola de AWS](https://console.aws.amazon.com/iam/):

1. **Política:** *IAM → Policies → Create policy → JSON*. Pega el contenido de
   `iam/deployer-policy.json`, *Next*, nombre `music-recommender-deployer`, *Create policy*.
2. **Usuario:** *IAM → Users → Create user*, nombre `music-recommender-deployer`. No marques
   acceso a la consola. *Next → Attach policies directly*, busca y marca
   `music-recommender-deployer`, *Next → Create user*.
3. **Llave de acceso:** abre el usuario → *Security credentials → Create access key* →
   *Command Line Interface (CLI)* → acepta el aviso → *Create access key*. Copia la *Access
   key* y la *Secret access key*: la secreta solo se muestra esta vez.
4. **Perfil en tu máquina:**

   ```bash
   aws configure --profile music-deployer
   ```

   Pega las dos llaves, región `us-east-1` y formato `json`. Las llaves quedan en
   `~/.aws/credentials`, fuera del repositorio.
5. **Probar:** debe mostrar `user/music-recommender-deployer`, no `root`.

   ```bash
   aws sts get-caller-identity --profile music-deployer
   ```

Antes de usar Terraform, indica el perfil en la terminal: `$env:AWS_PROFILE = "music-deployer"`
en PowerShell o `export AWS_PROFILE=music-deployer` en bash.

Cuidados:
- Nunca subas las llaves a Git ni las pegues en un chat. Si se filtran, desactívalas en
  *Security credentials* y crea otras.
- Activa MFA en la cuenta root (*IAM → Dashboard → Add MFA*) y no le crees llaves de acceso.
- Si un `apply` falla con `AccessDenied`, el mensaje dice qué acción faltó: agrégala a la
  política (*IAM → Policies → music-recommender-deployer → Edit*) y vuelve a correr `apply`.

## Desplegar

Desde la carpeta `infra/`:

**1. Configurar (opcional).** Sin `terraform.tfvars` se usan los valores por omisión: todo en
`us-east-1`, sin CD y sin avisos por correo.

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars`: pon tu repositorio en `github_repo` para activar el CD y tus correos
para alarmas y presupuesto.

**2. Descargar el proveedor de AWS** (solo la primera vez):

```bash
terraform init
```

**3. Revisar qué se va a crear.** No cambia nada en AWS; solo muestra el plan:

```bash
terraform plan
```

**4. Crear todo.** Escribe `yes` cuando lo pida. Tarda unos 5 minutos; casi todo es construir
y subir la imagen.

```bash
terraform apply
```

Al terminar imprime la URL de la API. Pruébala:

```bash
curl "$(terraform output -raw api_url)/health"
```

O abre `<api_url>/docs` en el navegador. La primera petición tarda varios segundos (arranque
en frío: la Lambda descarga y carga el modelo).

Si pusiste `alarm_email`, confirma el correo de suscripción que manda AWS.

**5. Activar el CD** (solo si definiste `github_repo`):

```bash
terraform output github_variables
```

Crea esas 5 variables en GitHub: *Settings → Secrets and variables → Actions → Variables*.
No son secretos: no hay llaves de acceso, GitHub obtiene credenciales temporales por OIDC.
Desde ahí, cada push a `main` que pase el CI se despliega solo (ver
[`.github/workflows/README.md`](../.github/workflows/README.md)).

## Actualizar

Terraform compara el código con lo que existe en AWS y solo cambia lo necesario:

| Cambio | Qué hacer | Qué pasa |
| --- | --- | --- |
| Reentrenaste el modelo | `terraform apply` | Sube el nuevo `recommender.joblib` (S3 conserva el anterior) y la Lambda arranca contenedores nuevos que lo cargan |
| Cambiaste código de `api/` o `src/` | Push a `main` (CD) o `terraform apply` | Se construye y se despliega una imagen nueva |
| Cambiaste algo de `infra/` | `terraform apply` | Solo se modifican los recursos afectados |

**¿Cómo sabe Terraform que cambió el código?** La etiqueta de la imagen es una huella
(`sha1`) de los archivos que entran a ella. Si cambia un archivo, cambia la etiqueta y
Terraform construye una imagen nueva; si nada cambió, no reconstruye.

**CD y Terraform a la vez.** El CD etiqueta las imágenes con el SHA del commit y Terraform
con la huella del código. Si después de un despliegue del CD corres `terraform apply`, la
Lambda vuelve a la imagen de Terraform, construida con el código de tu carpeta. Corre
`apply` con tu carpeta al día (`git pull`) para no regresar a código viejo.

## El estado de Terraform

`terraform.tfstate` es la "memoria" de Terraform: qué recursos creó y sus identificadores.
Se queda en tu máquina y no se sube a Git (`.gitignore`). Consecuencias:

- **Quien despliega es quien administra.** Si tu compañera corre `apply` en su máquina,
  Terraform no sabe que tú ya creaste todo e intentará crearlo otra vez (y fallará porque los
  nombres ya existen). Decidan quién despliega, o configuren un
  [backend en S3](https://developer.hashicorp.com/terraform/language/backend/s3) para
  compartir el estado.
- **No lo borres** mientras la infraestructura exista: sin él, Terraform ya no puede
  actualizarla ni destruirla y habría que borrar todo a mano desde la consola.

## Monitoreo

`monitoring.tf` crea:

- **Dashboard `music-recommender`**: invocaciones, errores y throttles de Lambda; latencia
  p50/p95 del modelo; canciones no encontradas; duración de Lambda; popularidad de lo
  recomendado (mediana, promedio y p90, para vigilar el sesgo de popularidad); canciones
  explícitas recomendadas; y tres tablas de CloudWatch Logs Insights: canciones que más salen
  en primer lugar (*hubs*), uso de los filtros y las últimas 50 predicciones.
- **Alarma `music-recommender-errores`**: al menos un error de Lambda en 5 minutos.
- **Alarma `music-recommender-latencia`**: p95 de `Latency` arriba de `latency_alarm_ms`
  (500 ms) durante 15 minutos.

Las dos avisan al tema SNS `music-recommender-alarmas`. La URL del dashboard se ve con
`terraform output dashboard_url`. Las métricas personalizadas las genera la API, ver
[`api/README.md`](../api/README.md#monitoreo).

## AWS Academy (Learner Lab)

Learner Lab no permite crear roles de IAM, proveedores OIDC ni presupuestos. En
`terraform.tfvars`:

```hcl
use_lab_role = true
github_repo  = ""
budget_email = ""
```

`use_lab_role` hace que la Lambda use el rol `LabRole` del laboratorio; Terraform arma su ARN
con el número de tu cuenta.

- Las credenciales del laboratorio están en *AWS Details → AWS CLI* y vencen al cerrar la
  sesión (unas 4 horas): cópialas a `~/.aws/credentials` cada vez que inicies el
  laboratorio. Si las guardas con un perfil con nombre (por ejemplo `[academy]`), indícalo
  antes de usar Terraform: `$env:AWS_PROFILE = "academy"` en PowerShell o
  `export AWS_PROFILE=academy` en bash.
- Sin rol de GitHub no hay CD automático: despliega los cambios con `terraform apply`.
- Al terminar la sesión del laboratorio los recursos se conservan, pero Lambda y API Gateway
  solo cobran por uso.

## Costos y limpieza

Con poco tráfico todo queda dentro de la capa gratuita o en centavos: Lambda y API Gateway
cobran por petición, S3 guarda ~30 MB y ECR unos cientos de MB. Lo que más cuesta es dejar
prendida una instancia de SageMaker.

Para borrar todo lo que creó Terraform, incluido el bucket con su contenido y las imágenes:

```bash
terraform destroy
```

Si prefieres que `destroy` falle mientras el bucket tenga archivos, pon
`force_destroy = false` en `terraform.tfvars`.
