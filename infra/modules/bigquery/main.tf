resource "google_bigquery_dataset" "civil_liberties_dataset" {
  dataset_id                  = var.dataset_id
  project                     = var.project_id
  location                    = var.region
  delete_contents_on_destroy  = true
}
variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for the dataset"
  type        = string
}
