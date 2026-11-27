#Glueデータベース & Athenaワークグループ
resource "aws_glue_catalog_database" "stock_db" {
  name = "${replace(var.project_name, "-", "_")}_${var.env}_db"
}

resource "aws_athena_workgroup" "stock_wg" {
  name = "${var.project_name}-${var.env}-wg"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = false
    # 1回のクエリでスキャンできるデータ量の上限を100MBに制限（意図しない高額課金の防止）
    bytes_scanned_cutoff_per_query     = 104857600

    result_configuration {
      #SQLの検索結果ファイルを保存するS3の場所（s3.tfで作った専用バケットを指定）
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/output/"
      #保存される検索結果ファイルを自動で暗号化する（セキュリティ対策）
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}
