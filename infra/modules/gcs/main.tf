resource "google_storage_bucket" "civil_liberties_bucket" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}
variable "bucket_name" {
  description = "Name of the GCS bucket"
  type        = string
}

variable "region" {
  description = "Region for the bucket"
  type        = string
}
