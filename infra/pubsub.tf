resource "google_pubsub_topic" "trigger-cloud-func" {
  name    = "${var.env}-trigger-cloud-func-trading-deribit-btc-perpetual-hourly"
  project = var.project

  labels  = {
    env       = var.env
    component = "trading-deribit-btc-perpetual-hourly"
  }

  depends_on = [
    google_project_service.gcp_services,
  ]
}
