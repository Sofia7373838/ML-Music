# AWS Budgets: aviso por correo si el gasto se acerca al límite. Solo si hay correo.

resource "aws_budgets_budget" "monthly" {
  count        = var.budget_email != "" ? 1 : 0
  name         = "${var.project_name}-mensual"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Aviso cuando el gasto real pasa del 80 %.
  notification {
    notification_type          = "ACTUAL"
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.budget_email]
  }

  # Aviso cuando el pronóstico del mes pasa del 100 %.
  notification {
    notification_type          = "FORECASTED"
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.budget_email]
  }
}
