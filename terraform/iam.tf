#最小権限のIAMロール・ポリシー

#誰がこの身分証を使えるか？
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

#IAMロールの「箱」を作る
resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-${var.env}-lambda-role"
  #上で作った信頼ポリシーのJSON（.json）をセット
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

#AWS公式の基本権限をつける
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

#今回のアプリ専用の許可証を作る
data "aws_iam_policy_document" "lambda_etl_policy" {
  #SSM Parameter Storeの読み取り
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter"
    ]
    #今回作ったAlpha VantageのAPIキーのARNだけに限定
    resources = [aws_ssm_parameter.alphavantage_api_key.arn]
  }

#S3データレイクへの読み書き
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket"
    ]
    #data_lake バケット本体とその中身（/*）だけに限定
    resources = [
      aws_s3_bucket.data_lake.arn,
      "${aws_s3_bucket.data_lake.arn}/*"
    ]
  }

  #Glue Data Catalogへのテーブル・パーティション登録
  statement {
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetTable",
      "glue:CreateTable",
      "glue:UpdateTable",
      "glue:GetPartitions",
      "glue:CreatePartition",
      "glue:BatchCreatePartition"
    ]
    resources = [
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${aws_glue_catalog_database.stock_db.name}",
      "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${aws_glue_catalog_database.stock_db.name}/*"
    ]
  }
}

#許可証をロールへ貼り付ける
resource "aws_iam_role_policy" "lambda_etl" {
  name   = "${var.project_name}-${var.env}-lambda-etl-policy"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_etl_policy.json
}
