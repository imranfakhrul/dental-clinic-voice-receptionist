output "access_policy_id" {
  description = "Access policy ID for P1-02 and P1-06."
  value       = google_access_context_manager_access_policy.org.name
}

output "perimeter_names" {
  description = "Perimeter name per environment."
  value = {
    prod    = google_access_context_manager_service_perimeter.prod.title
    dev     = google_access_context_manager_service_perimeter.dry_run["dev"].title
    staging = google_access_context_manager_service_perimeter.dry_run["staging"].title
  }
}

output "allowed_apis" {
  description = "APIs on the folder allow-list (restrictServiceUsage-supported entries of allowed_services.yaml)."
  value       = local.allowed_apis
}
