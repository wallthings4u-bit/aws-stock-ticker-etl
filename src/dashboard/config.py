# AWSリソース設定（Terraformで構築したリソースと一致）
AWS_REGION = "ap-northeast-1"
GLUE_DATABASE = "aws_stock_ticker_etl_dev_db"
GLUE_TABLE = "stock_quotes"
ATHENA_WORKGROUP = "aws-stock-ticker-etl-dev-wg"

# キャッシュ有効期限（秒）: 10分
CACHE_TTL_SECONDS = 600

# 為替レート識別子とフォールバック設定
FX_SYMBOL = "USDJPY"
DEFAULT_USDJPY_RATE = 150.0

# 表示通貨の選択肢
CURRENCY_OPTIONS = ["USD ($)", "JPY (¥)"]

# 株式銘柄コードと日本語表示名のマッピング（為替レコードは含めない）
TICKER_LABELS = {
    "EWJ": "EWJ (日経平均連動ETF)",
    "DIA": "DIA (ダウ平均連動ETF)",
    "TM": "TM (トヨタ自動車)",
    "SMFG": "SMFG (三井住友FG)",
    "NVDA": "NVDA (NVIDIA)",
    "TSLA": "TSLA (Tesla)",
    "ARM": "ARM (Arm Holdings)",
}
