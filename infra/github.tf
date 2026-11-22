# Rol que asume GitHub Actions (workflow de CD) por OIDC: sin llaves de acceso guardadas.
# Solo se crea si se define `github_repo`.

resource "aws_iam_openid_connect_provider" "github" {
  count          = local.enable_github && var.create_github_oidc_provider ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

# Si la cuenta ya tenía el proveedor (solo puede haber uno), se reutiliza.
data "aws_iam_openid_connect_provider" "github" {
  count = local.enable_github && !var.create_github_oidc_provider ? 1 : 0
  url   = "https://token.actions.githubusercontent.com"
}

locals {
  github_oidc_arn = (
    var.create_github_oidc_provider
    ? one(aws_iam_openid_connect_provider.github[*].arn)
    : one(data.aws_iam_openid_connect_provider.github[*].arn)
  )
}

# Solo la rama main de este repositorio puede asumir el rol. Ojo: si el job de CD usara
# `environment:`, el claim `sub` cambiaría y AWS rechazaría el token.
resource "aws_iam_role" "github_actions" {
  count = local.enable_github ? 1 : 0
  name  = "${var.project_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.github_oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

# Permisos mínimos del CD: subir imágenes a este ECR y actualizar solo esta Lambda.
resource "aws_iam_role_policy" "github_actions_deploy" {
  count = local.enable_github ? 1 : 0
  name  = "deploy"
  role  = aws_iam_role.github_actions[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = aws_ecr_repository.api.arn
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:UpdateFunctionCode",
        ]
        Resource = aws_lambda_function.api.arn
      },
    ]
  })
}
