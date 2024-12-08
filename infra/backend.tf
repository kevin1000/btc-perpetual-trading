terraform {
  backend "gcs" {
    bucket = "trading-etl-deribit-btc-perpetual-ao-signals-tf-state"
  }
}
