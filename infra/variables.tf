variable "project" {
  type = string
  description = "GCP project ID"
}

variable "env" {
  type = string
  description = "Environment"
}

variable "region" {
  type = string
  description = "Region where to deploy infra"
  default = "europe-west2"
}

variable "gcp_service_list" {
  description = "List of GCP service to be enabled for a project."
  type        = list
  default     = ["cloudresourcemanager.googleapis.com", "notebooks.googleapis.com", "bigquery.googleapis.com", "pubsub.googleapis.com",
                 "cloudscheduler.googleapis.com", "appengine.googleapis.com", "cloudfunctions.googleapis.com", "secretmanager.googleapis.com"]
}
