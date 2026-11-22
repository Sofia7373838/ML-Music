# Amazon ECR: el registro donde vive la imagen Docker de la API.

resource "aws_ecr_repository" "api" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"
  # Las imágenes se reconstruyen desde el código, así que destroy puede borrarlas.
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar solo las ultimas 10 imagenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# Construye la imagen y la sube a ECR con los comandos de Docker de la máquina que corre
# Terraform. Solo se vuelve a ejecutar cuando cambia el código (cambia `image_tag`).
#
# - `--platform linux/amd64`: Lambda corre en x86_64, aunque construyas en una Mac M1.
# - `--provenance=false`: Lambda no acepta los manifiestos multiplataforma que Docker
#   Buildx genera por omisión.
# - Los comandos se unen con && y no usan nada propio de una shell, así funcionan igual
#   en Windows (cmd) que en macOS y Linux (sh).
resource "terraform_data" "image" {
  triggers_replace = [local.image_uri]

  provisioner "local-exec" {
    working_dir = local.repo_root
    command = join(" && ", [
      "aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${split("/", aws_ecr_repository.api.repository_url)[0]}",
      "docker build --platform linux/amd64 --provenance=false -t ${local.image_uri} .",
      "docker push ${local.image_uri}",
    ])
  }
}
