# Amazon S3: datos y modelo, con versionado para conservar cada versión del modelo.

resource "aws_s3_bucket" "artifacts" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "borrar-versiones-viejas"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  depends_on = [aws_s3_bucket_versioning.artifacts]
}

# El modelo que carga la Lambda. `source_hash` hace que Terraform lo vuelva a subir cada
# vez que se reentrena (el archivo cambia), y S3 guarda la versión anterior.
resource "aws_s3_object" "model" {
  bucket      = aws_s3_bucket.artifacts.id
  key         = local.model_key
  source      = local.model_path
  source_hash = fileexists(local.model_path) ? filemd5(local.model_path) : null

  lifecycle {
    precondition {
      condition     = fileexists(local.model_path)
      error_message = "No existe models/recommender.joblib. Entrena primero: python -m recommender.train"
    }
  }

  depends_on = [aws_s3_bucket_versioning.artifacts]
}

# Copias de los datos y del reporte de métricas, solo si existen en la máquina.
locals {
  optional_uploads = {
    "data/raw/dataset.csv"            = "${local.repo_root}/data/raw/dataset.csv"
    "data/processed/tracks_clean.csv" = "${local.repo_root}/data/processed/tracks_clean.csv"
    "models/metrics.json"             = "${local.repo_root}/models/metrics.json"
  }
  uploads = {
    for key, path in local.optional_uploads : key => path
    if var.upload_datasets && fileexists(path)
  }
}

resource "aws_s3_object" "data" {
  for_each = local.uploads

  bucket      = aws_s3_bucket.artifacts.id
  key         = each.key
  source      = each.value
  source_hash = filemd5(each.value)

  depends_on = [aws_s3_bucket_versioning.artifacts]
}
