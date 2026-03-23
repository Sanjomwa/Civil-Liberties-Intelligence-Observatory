output "bucket_name" {
  value = module.gcs.bucket_name
}

output "dataset_id" {
  value = module.bigquery.dataset_id
}
