#平日毎日2回の自動実行スケジュール
resource "aws_cloudwatch_event_rule" "twice_daily" {
  name                = "${var.project_name}-${var.env}-schedule"
  description         = "Trigger stock ETL twice a day"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.twice_daily.name
  target_id = "StockETLLambda"
  arn       = aws_lambda_function.stock_etl.arn
}

#Lambda関数（処理本体）を起動（実行）するための『入場許可証（ドアの鍵）』を渡す設定
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  #許可する操作（＝Lambda関数を実行すること）
  action        = "lambda:InvokeFunction"
  # どのLambda関数へのドアを開けるか（今回作る株価収集Lambdaを指定）
  function_name = aws_lambda_function.stock_etl.function_name
  #誰に許可するか（＝AWSのEventBridgeサービス全体）
  principal     = "events.amazonaws.com"
  #「今回作った毎日2回のタイマー(ARN)」からの呼び出しだけに限定する
  source_arn    = aws_cloudwatch_event_rule.twice_daily.arn
}
