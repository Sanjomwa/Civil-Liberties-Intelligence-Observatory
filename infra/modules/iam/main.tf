resource "google_project_iam_member" "admin" {
  project = var.project_id
  role    = "roles/editor"
  member  = "user:${var.admin_email}"
}