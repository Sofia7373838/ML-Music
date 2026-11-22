# Amazon API Gateway: la URL pública de la API.
#
# "Quick create": al dar `target`, la HTTP API crea sola su ruta $default (todas las
# rutas van a la Lambda), la integración y la etapa con despliegue automático.

resource "aws_apigatewayv2_api" "http" {
  name          = local.function_name
  protocol_type = "HTTP"
  target        = aws_lambda_function.api.arn
}

# Sin este permiso, API Gateway no puede invocar la Lambda.
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*"
}
