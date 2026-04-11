resource "google_storage_bucket" "main" {
  name          = var.bucket_name
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

output "bucket_name" {
  value = google_storage_bucket.main.name
}