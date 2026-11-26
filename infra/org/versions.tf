terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  # Apply as a member of gcp-security-admins with: gcloud auth application-default login
  # Quota project for org-level APIs; never a PHI project.
  billing_project       = var.ops_project_id
  user_project_override = true
}
