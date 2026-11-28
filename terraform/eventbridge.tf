# 平日毎日2回の自動実行スケジュール
resource "aws_cloudwatch_event_rule" "twice_daily" {
  name                = "${var.project_name}-${var.env}-schedule"
  description         = "Trigger stock ETL twice a day"
  schedule_expression = var.schedule_expression
}

# 定期実行のターゲットを本番エイリアス（live）に向ける
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.twice_daily.name
  target_id = "StockETLLambda"
  arn       = aws_lambda_alias.live.arn
}

# Lambdaの本番エイリアス（live）を起動するための『入場許可証（ドアの鍵）』を渡す設定
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id = "AllowExecutionFromEventBridge"
  # 許可する操作（＝Lambda関数を実行すること）
  action = "lambda:InvokeFunction"
  # どのLambda関数へのドアを開けるか
  function_name = aws_lambda_function.stock_etl.function_name
  # 対象エイリアス（live）を明示指定
  qualifier = aws_lambda_alias.live.name
  # 誰に許可するか（＝AWSのEventBridgeサービス全体）
  principal = "events.amazonaws.com"
  # 「今回作った毎日2回のタイマー(ARN)」からの呼び出しだけに限定する
  source_arn = aws_cloudwatch_event_rule.twice_daily.arn
}
