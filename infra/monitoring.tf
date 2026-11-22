# Amazon CloudWatch y SNS: alarmas, avisos por correo y dashboard.
# Las métricas del namespace MusicRecommender las genera la API (api/monitoring.py).

resource "aws_sns_topic" "alarms" {
  name = "${var.project_name}-alarmas"
}

# AWS manda un correo de confirmación: hay que aceptarlo para recibir las alarmas.
resource "aws_sns_topic_subscription" "alarm_email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.project_name}-errores"
  alarm_description   = "La función Lambda falló al menos una vez en 5 minutos."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.api.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "latency" {
  alarm_name          = "${var.project_name}-latencia"
  alarm_description   = "El p95 de latencia de las recomendaciones pasó el umbral."
  namespace           = "MusicRecommender"
  metric_name         = "Latency"
  dimensions          = { Endpoint = "recommendations" }
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 3
  threshold           = var.latency_alarm_ms
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

locals {
  log_source = "SOURCE '${aws_cloudwatch_log_group.api.name}'"
  fn         = aws_lambda_function.api.function_name

  dashboard_widgets = [
    {
      type = "metric", x = 0, y = 0, width = 12, height = 6
      properties = {
        title = "Invocaciones y errores", region = var.region, stat = "Sum", period = 300
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", local.fn],
          [".", "Errors", ".", "."],
          [".", "Throttles", ".", "."],
        ]
      }
    },
    {
      type = "metric", x = 12, y = 0, width = 12, height = 6
      properties = {
        title = "Latencia del modelo (ms)", region = var.region, period = 300
        metrics = [
          ["MusicRecommender", "Latency", "Endpoint", "recommendations", { stat = "p50", label = "p50" }],
          ["...", { stat = "p95", label = "p95" }],
        ]
      }
    },
    {
      type = "metric", x = 0, y = 6, width = 12, height = 6
      properties = {
        title   = "Canciones no encontradas", region = var.region, stat = "Sum", period = 300
        metrics = [["MusicRecommender", "SongNotFound", "Endpoint", "recommendations"]]
      }
    },
    {
      type = "metric", x = 12, y = 6, width = 12, height = 6
      properties = {
        title = "Duración de Lambda (ms)", region = var.region, period = 300
        metrics = [
          ["AWS/Lambda", "Duration", "FunctionName", local.fn, { stat = "p95", label = "p95" }],
          ["...", { stat = "Maximum", label = "máximo" }],
        ]
      }
    },
    {
      type = "metric", x = 0, y = 12, width = 12, height = 6
      properties = {
        title  = "Popularidad de lo recomendado (sesgo de popularidad)"
        region = var.region, period = 3600
        yAxis  = { left = { min = 0, max = 100 } }
        metrics = [
          ["MusicRecommender", "RecommendedPopularity", "Endpoint", "recommendations", { stat = "p50", label = "mediana" }],
          ["...", { stat = "Average", label = "promedio" }],
          ["...", { stat = "p90", label = "p90" }],
        ]
      }
    },
    {
      type = "metric", x = 12, y = 12, width = 12, height = 6
      properties = {
        title   = "Canciones explícitas recomendadas", region = var.region, stat = "Sum", period = 3600
        metrics = [["MusicRecommender", "ExplicitRecommended", "Endpoint", "recommendations"]]
      }
    },
    {
      type = "log", x = 0, y = 18, width = 12, height = 6
      properties = {
        title  = "Hubs: canciones que más salen en primer lugar"
        region = var.region, view = "table"
        query  = "${local.log_source} | filter Endpoint = 'recommendations' and SongNotFound = 0 | stats count(*) as listas by `recommended_ids.0` | sort listas desc | limit 20"
      }
    },
    {
      type = "log", x = 12, y = 18, width = 12, height = 6
      properties = {
        title  = "Uso de los filtros (descubrimiento, explícito, tope por artista)"
        region = var.region, view = "table"
        query  = "${local.log_source} | filter Endpoint = 'recommendations' | stats count(*) as peticiones by ispresent(max_popularity) as descubrimiento, exclude_explicit, max_per_artist"
      }
    },
    {
      type = "log", x = 0, y = 24, width = 24, height = 6
      properties = {
        title  = "Últimas predicciones"
        region = var.region, view = "table"
        query  = "${local.log_source} | fields @timestamp, track_id, k, Recommendations, Latency, SongNotFound, exclude_explicit, max_per_artist | filter Endpoint = 'recommendations' | sort @timestamp desc | limit 50"
      }
    },
  ]
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = var.project_name
  dashboard_body = jsonencode({ widgets = local.dashboard_widgets })
}
