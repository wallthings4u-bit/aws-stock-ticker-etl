# terraform apply 完了時に、後続のCLI操作やアプリ設定で使うリソース名をターミナルに表示する
output "ssm_parameter_name" {
  description = "APIキーを登録するSSM Parameter Storeのパス"
  value       = aws_ssm_parameter.alphavantage_api_key.name
}

output "datalake_bucket_name" {
  description = "Parquetデータが保存されるS3バケット名"
  value       = aws_s3_bucket.data_lake.bucket
}

output "lambda_function_name" {
  description = "作成されたLambda関数名"
  value       = aws_lambda_function.stock_etl.function_name
}

output "glue_database_name" {
  description = "Glue Data Catalogのデータベース名"
  value       = aws_glue_catalog_database.stock_db.name
}

output "athena_workgroup_name" {
  description = "Athenaのワークグループ名"
  value       = aws_athena_workgroup.stock_wg.name
}
