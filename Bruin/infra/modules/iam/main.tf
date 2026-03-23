resource "google_project_iam_member" "civil_liberties_admin" {
  project = var.project_id
  role    = "roles/editor"
  member  = "user:${var.admin_email}"
}
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "admin_email" {
  description = "Admin email for IAM binding"
  type        = string
}
