terraform {
  required_version = ">= 1.5.0"
}

module "gcs" {
  source      = "./modules/gcs"
  bucket_name = var.bucket_name
  region      = var.region
}

module "bigquery" {
  source              = "./modules/bigquery"
  project_id          = var.project_id
  region              = var.region
  prod_dataset_id     = var.prod_dataset_id
  staging_dataset_id  = var.staging_dataset_id
}

module "iam" {
  source      = "./modules/iam"
  project_id  = var.project_id
  admin_email = var.admin_email
}

output "bucket_name" {
  value = module.gcs.bucket_name
}

output "prod_dataset" {
  value = module.bigquery.prod_dataset_id
}

output "staging_dataset" {
  value = module.bigquery.staging_dataset_id
}