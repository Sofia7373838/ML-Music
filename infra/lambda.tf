# AWS Lambda: ejecuta la API (FastAPI + Mangum) desde la imagen de ECR.

# Rol con permisos mínimos: escribir sus logs y leer solo el archivo del modelo.
# No se crea si se pasa `lambda_role_arn` (por ejemplo LabRole en Learner Lab).
resource "aws_iam_role" "lambda" {
  count = local.create_lambda_role ? 1 : 0
  name  = "${local.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  count      = local.create_lambda_role ? 1 : 0
  role       = aws_iam_role.lambda[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_read_model" {
  count = local.create_lambda_role ? 1 : 0
  name  = "leer-modelo"
  role  = aws_iam_role.lambda[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:GetObject"
      Resource = "${aws_s3_bucket.artifacts.arn}/${local.model_key}"
    }]
  })
}

# Se crea antes que la función para controlar cuántos días se guardan los logs.
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "api" {
  function_name = local.function_name
  package_type  = "Image"
  image_uri     = local.image_uri
  architectures = ["x86_64"]
  role          = local.lambda_role_arn
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_s

  environment {
    variables = {
      MODEL_S3_URI = "s3://${aws_s3_bucket.artifacts.id}/${local.model_key}"
      # La Lambda carga el modelo una vez por contenedor. Cuando se sube un modelo nuevo,
      # cambia esta variable y AWS arranca contenedores nuevos que cargan esa versión.
      MODEL_VERSION = aws_s3_object.model.version_id
    }
  }

  depends_on = [
    terraform_data.image,
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy.lambda_read_model,
  ]
}
