variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Region for the dataset"
  type        = string
}

variable "prod_dataset_id" {
  description = "BigQuery dataset ID for production"
  type        = string
}

variable "staging_dataset_id" {
  description = "BigQuery dataset ID for staging"
  type        = string
}