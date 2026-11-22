# Valores calculados que usan varios archivos.

data "aws_caller_identity" "current" {}

locals {
  repo_root     = abspath("${path.module}/..")
  account_id    = data.aws_caller_identity.current.account_id
  function_name = "${var.project_name}-api"
  # El nombre de un bucket es único en todo AWS: el número de cuenta evita choques.
  bucket_name = "${var.project_name}-${local.account_id}"

  model_key  = "models/recommender.joblib"
  model_path = "${local.repo_root}/models/recommender.joblib"

  # Archivos que entran a la imagen de Docker (los mismos que permite .dockerignore).
  # Si cambia cualquiera, cambia la etiqueta y Terraform construye una imagen nueva.
  image_files = sort(concat(
    ["Dockerfile", ".dockerignore", "requirements.txt", "requirements-api.txt"],
    tolist(fileset(local.repo_root, "src/recommender/*.py")),
    tolist(fileset(local.repo_root, "api/*.py")),
  ))
  image_tag = substr(sha1(join("", [
    for f in local.image_files : filesha1("${local.repo_root}/${f}")
  ])), 0, 12)
  image_uri = "${aws_ecr_repository.api.repository_url}:${local.image_tag}"

  # Rol de la Lambda, en este orden: LabRole de Learner Lab, un rol que ya existe, o uno
  # nuevo que crea Terraform. one() regresa el único elemento de una lista o null si está
  # vacía: los recursos con `count = 0` (no creados) no rompen la expresión.
  lab_role_arn       = "arn:aws:iam::${local.account_id}:role/LabRole"
  create_lambda_role = !var.use_lab_role && var.lambda_role_arn == ""
  lambda_role_arn = (
    var.use_lab_role ? local.lab_role_arn
    : var.lambda_role_arn != "" ? var.lambda_role_arn
    : one(aws_iam_role.lambda[*].arn)
  )
  enable_github = var.github_repo != ""
}
