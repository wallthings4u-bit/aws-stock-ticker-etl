#Lambda関数の設定
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda"
  output_path = "${path.module}/.build/lambda_function.zip"
}

# CloudWatch Logs の保持期間設定（14日で自動削除して課金・肥大化を防止）
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.project_name}-${var.env}-collector"
  retention_in_days = 14
}

#AWS上にLambda関数を作成するための設計図（スペック表＋プログラム本体の指定）
resource "aws_lambda_function" "stock_etl" {
  function_name    = "${var.project_name}-${var.env}-collector"
  role             = aws_iam_role.lambda_exec.arn
  #最初に実行するPythonファイル名と関数名（handler.pyの中の「lambda_handler関数」）
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  timeout          = 180
  memory_size      = 512
  #アップロードするZIPファイルのパス
  filename         = data.archive_file.lambda_zip.output_path
  #ZIPファイルのハッシュ値:handler.pyを書き換えた時にTerraformが変更を検知して再アップロードするために必須
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # デプロイごとに不変のバージョン番号（1, 2, 3...）を発行する（エイリアス運用に必須）
  publish = true

  #追加パッケージ（AWS公式のAWSSDKPandas Layer）をアタッチ
  layers = [var.awswrangler_layer_arn]

  environment {
    variables = {
      SSM_API_KEY_NAME = aws_ssm_parameter.alphavantage_api_key.name
      S3_BUCKET_NAME   = aws_s3_bucket.data_lake.bucket
      GLUE_DATABASE    = aws_glue_catalog_database.stock_db.name
      GLUE_TABLE       = "stock_quotes"
      TARGET_TICKERS   = var.target_tickers
    }
  }
}

# 本番用エイリアス（あだ名: live）の作成
# GitHub Actionsでのテスト合格後、このエイリアスが指すバージョン番号を切り替える
resource "aws_lambda_alias" "live" {
  name             = "live"
  description      = "Production alias updated safely after CI smoke test"
  function_name    = aws_lambda_function.stock_etl.function_name
  function_version = aws_lambda_function.stock_etl.version

  # GitHub Actions側で切り替えたバージョン番号をTerraformが上書きしないよう保護
  lifecycle {
    ignore_changes = [function_version]
  }
}