# Lo que Terraform imprime al terminar `apply`. Se vuelve a ver con `terraform output`.

output "api_url" {
  description = "URL pública de la API. Prueba: <api_url>/health y <api_url>/docs"
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "dashboard_url" {
  description = "Dashboard de CloudWatch."
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "bucket_name" {
  value = aws_s3_bucket.artifacts.id
}

output "model_s3_uri" {
  value = "s3://${aws_s3_bucket.artifacts.id}/${local.model_key}"
}

output "image_uri" {
  value = local.image_uri
}

output "function_name" {
  value = aws_lambda_function.api.function_name
}

# Valores para GitHub → Settings → Secrets and variables → Actions → Variables.
output "github_variables" {
  description = "Variables del repositorio que activan el workflow de CD."
  value = local.enable_github ? {
    AWS_REGION      = var.region
    AWS_ROLE_ARN    = one(aws_iam_role.github_actions[*].arn)
    ECR_REPOSITORY  = aws_ecr_repository.api.name
    LAMBDA_FUNCTION = aws_lambda_function.api.function_name
    API_URL         = aws_apigatewayv2_api.http.api_endpoint
  } : null
}
