resource "google_bigquery_dataset" "prod" {
  dataset_id                 = var.prod_dataset_id
  project                    = var.project_id
  location                   = var.region
  delete_contents_on_destroy = false
}

resource "google_bigquery_dataset" "staging" {
  dataset_id                 = var.staging_dataset_id
  project                    = var.project_id
  location                   = var.region
  delete_contents_on_destroy = true
}

output "prod_dataset_id" {
  value = google_bigquery_dataset.prod.dataset_id
}

output "staging_dataset_id" {
  value = google_bigquery_dataset.staging.dataset_id
}