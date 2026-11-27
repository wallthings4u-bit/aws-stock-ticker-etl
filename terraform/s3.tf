#データレイク用 & Athena結果用バケット

#収集した株価Parquetファイルを永続保存するためのS3バケット本体を作成
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project_name}-${var.env}-datalake-${data.aws_caller_identity.current.account_id}"
}

#バケットに保存されるすべてのファイルを、AWS側で自動的に暗号化（AES256 ＝ SSE-S3）
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

#インターネットからの一般公開を完全に遮断
resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

#Athenaのクエリ結果一時保存用

#SQLを実行した際に出力される検索結果を保管するS3バケットの作成
resource "aws_s3_bucket" "athena_results" {
  bucket = "${var.project_name}-${var.env}-athena-${data.aws_caller_identity.current.account_id}"
}

#インターネットからの一般公開を完全に遮断
resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

#作成から7日経過したファイルを自動削除するライフサイクルルール設定
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    expiration {
      days = 7
    }
  }
}
