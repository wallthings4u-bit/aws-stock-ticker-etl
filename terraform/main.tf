#AWS接続設定と共通タグ
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.env
      ManagedBy   = "Terraform"
    }
  }
}

#今 Terraform を実行している AWSアカウントの情報（特に12桁のアカウントID）を自動取得
#s3.tf でバケット名を世界中で一意にするため
#iam.tf でGlueのARN（住所）を組み立てるため
data "aws_caller_identity" "current" {}
