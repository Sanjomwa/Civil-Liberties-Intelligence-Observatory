module "gcs" {
  source      = "./modules/gcs"
  bucket_name = var.bucket_name
  region      = var.region
}

module "bigquery" {
  source      = "./modules/bigquery"
  dataset_id  = var.dataset_id
  project_id  = var.project_id
  region      = var.region
}

module "iam" {
  source      = "./modules/iam"
  project_id  = var.project_id
  admin_email = var.admin_email
}
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
  description = "Name of GCS bucket"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}

variable "admin_email" {
  description = "Admin email for IAM"
  type        = string
}
