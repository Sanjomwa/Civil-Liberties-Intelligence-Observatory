project_id          = "encoded-joy-485413-k5"
region              = "us-central1"
bucket_name         = "civil-liberties-data"
prod_dataset_id     = "civil_liberties_prod"      # (no hyphens)
staging_dataset_id  = "civil_liberties_staging"   # (no hyphens)
# Placeholder only. Set the real value locally, via the TF_VAR_admin_email
# environment variable or a -var-file kept outside this repository (this
# folder's .gitignore does not cover *.tfvars files); do not commit a
# personal address here.
admin_email         = "OWNER_EMAIL_PLACEHOLDER"