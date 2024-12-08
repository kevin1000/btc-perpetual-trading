resource "google_pubsub_topic" "trigger-cloud-func" {
  name    = "${var.env}-trigger-cloud-func-trading-btc-perpetual-ao-signals"
  project = var.project

  labels  = {
    env       = var.env
    component = "trading-btc-perpetual-ao-signals"
  }

  depends_on = [
    google_project_service.gcp_services,
  ]
}
