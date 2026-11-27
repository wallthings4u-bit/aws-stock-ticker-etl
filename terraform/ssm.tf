#APIキーの暗号化保管
resource "aws_ssm_parameter" "alphavantage_api_key" {
  name        = "/${var.project_name}/${var.env}/alphavantage_api_key"

   #AWSマネジメントコンソール画面に表示される説明メモ欄への入力
  description = "Alpha Vantage API Key (Set actual value via AWS CLI or Console)"
 
  #保存形式:SecureString→AWS KMS(暗号鍵)を使用して自動的に暗号化して保存
  type        = "SecureString"

  #初回作成時に入れる仮のダミー文字列
  value       = "PLACEHOLDER_SET_VIA_CLI"

  #Terraformのライフサイクル制御ブロック
  #中身の value（値）が変わっていても無視して触らないようにする
  lifecycle {
    ignore_changes = [value]
  }
}

