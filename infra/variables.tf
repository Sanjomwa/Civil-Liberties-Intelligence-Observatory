variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Default region"
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "Name of GCS bucket for raw/staging data"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}
