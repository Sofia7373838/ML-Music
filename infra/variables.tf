# Lo que cada quien puede ajustar. Se cambian en terraform.tfvars (ver el .example).
# Todas tienen un valor por omisión: con solo credenciales de AWS ya se puede desplegar.

variable "region" {
  description = "Región de AWS donde se crea todo."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefijo de los nombres de los recursos (bucket, ECR, Lambda, dashboard)."
  type        = string
  default     = "music-recommender"

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Solo minúsculas, números y guiones (los buckets de S3 no aceptan otra cosa)."
  }
}

# --- Permisos -----------------------------------------------------------------------

variable "use_lab_role" {
  description = <<-EOT
    true en AWS Academy (Learner Lab): ahí no se pueden crear roles de IAM y la Lambda usa
    el rol LabRole que ya existe. Terraform arma su ARN con el número de tu cuenta.
  EOT
  type        = bool
  default     = false
}

variable "lambda_role_arn" {
  description = <<-EOT
    Rol de IAM ya existente para la Lambda (ARN completo). Vacío = Terraform crea uno con
    permisos mínimos. Se ignora si `use_lab_role = true`.
  EOT
  type        = string
  default     = ""
}

variable "github_repo" {
  description = <<-EOT
    Repositorio de GitHub (owner/nombre) que puede desplegar con el workflow de CD.
    Vacío = no se crea el rol de GitHub Actions (el CD queda desactivado).
  EOT
  type        = string
  default     = ""

  validation {
    condition     = var.github_repo == "" || can(regex("^[^/]+/[^/]+$", var.github_repo))
    error_message = "Usa el formato owner/nombre, por ejemplo mi-usuario/ML-Music."
  }
}

variable "github_oidc_subject_prefix" {
  description = <<-EOT
    Solo si el repositorio usa sujetos inmutables en sus tokens OIDC (incluyen los IDs de la
    cuenta y del repositorio). Se obtiene con:
      gh api repos/<owner>/<repo>/actions/oidc/customization/sub --jq .sub_claim_prefix
    Ejemplo: "repo:mi-usuario@123456/ML-Music@7890123". Vacío = solo el formato clásico.
  EOT
  type        = string
  default     = ""

  validation {
    condition     = var.github_oidc_subject_prefix == "" || startswith(var.github_oidc_subject_prefix, "repo:")
    error_message = "Debe empezar con repo:, tal como lo regresa la API de GitHub."
  }
}

variable "create_github_oidc_provider" {
  description = <<-EOT
    true = crear el proveedor OIDC de GitHub. Solo puede existir uno por cuenta: si la
    cuenta ya lo tiene (otro proyecto lo creó), usa false y se reutiliza.
  EOT
  type        = bool
  default     = true
}

# --- Lambda ---------------------------------------------------------------------------

variable "lambda_memory_mb" {
  description = <<-EOT
    Memoria de la Lambda. AWS asigna CPU en proporción a la memoria: con 2048 MB el
    arranque en frío (importar pandas/scikit-learn y cargar el modelo) baja de 10 s.
  EOT
  type        = number
  default     = 2048
}

variable "lambda_timeout_s" {
  description = "Tiempo máximo de una petición, en segundos."
  type        = number
  default     = 30
}

# --- Monitoreo y costos ---------------------------------------------------------------

variable "log_retention_days" {
  description = "Días que CloudWatch guarda los logs de la API."
  type        = number
  default     = 14
}

variable "latency_alarm_ms" {
  description = "p95 de latencia del modelo (ms) que dispara la alarma."
  type        = number
  default     = 500
}

variable "alarm_email" {
  description = "Correo que recibe las alarmas. Vacío = las alarmas existen pero no avisan."
  type        = string
  default     = ""
}

variable "budget_email" {
  description = "Correo para la alerta de AWS Budgets. Vacío = sin presupuesto (Learner Lab no lo permite)."
  type        = string
  default     = ""
}

variable "budget_limit_usd" {
  description = "Gasto mensual (USD) contra el que se mide el presupuesto."
  type        = number
  default     = 10
}

# --- Datos ----------------------------------------------------------------------------

variable "upload_datasets" {
  description = "Subir también dataset.csv, tracks_clean.csv y metrics.json a S3 si existen."
  type        = bool
  default     = true
}

variable "force_destroy" {
  description = <<-EOT
    true = `terraform destroy` borra el bucket aunque tenga archivos. Todo lo que guarda se
    puede regenerar (el modelo se reentrena y el dataset se descarga de Kaggle).
  EOT
  type        = bool
  default     = true
}
