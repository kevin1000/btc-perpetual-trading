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


resource "google_pubsub_subscription" "cloud_func_subscription" {
     name  = "${var.env}-subscription-trading-deribit-btc-perpetual-hourly"
     topic = google_pubsub_topic.trigger-cloud-func.name

     project = var.project
     ack_deadline_seconds = 20
}