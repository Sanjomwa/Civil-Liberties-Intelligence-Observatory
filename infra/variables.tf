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
  description = "GCS bucket name"
  type        = string
}

variable "prod_dataset_id" {
  description = "BigQuery PROD dataset ID"
  type        = string
}

variable "staging_dataset_id" {
  description = "BigQuery STAGING dataset ID"
  type        = string
}

variable "admin_email" {
  description = "Admin email for IAM"
  type        = string
}