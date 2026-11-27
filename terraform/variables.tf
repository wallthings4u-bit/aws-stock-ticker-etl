#プロジェクト名・銘柄・スケジュール設定
variable "aws_region" {
  description = "デプロイ先AWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "プロジェクト名"
  type        = string
  default     = "aws-stock-ticker-etl"
}

variable "env" {
  description = "環境名"
  type        = string
  default     = "dev"
}

variable "target_tickers" {
  description = "取得対象の銘柄コード（日経連動EWJ + ダウ連動DIA + 日米主要5社）"
  type        = string
  default     = "EWJ,DIA,TM,SMFG,NVDA,TSLA,ARM"
}

variable "schedule_expression" {
  description = "EventBridgeスケジュール（平日のみ毎日2回：JST 08:00 と 16:00 ＝ UTC 23:00 と 07:00）"
  type        = string
  default     = "cron(0 23,7 ? * MON-FRI *)"
}

## Parquet変換・S3保存用のAWS公式ライブラリ（AWSSDKPandas）のLayer ARN
variable "awswrangler_layer_arn" {
  description = "AWS SDK for pandas (Python 3.12 / ap-northeast-1) 公式Layer ARN"
  type        = string
  default     = "arn:aws:lambda:ap-northeast-1:336392948345:layer:AWSSDKPandas-Python312:13"
}
