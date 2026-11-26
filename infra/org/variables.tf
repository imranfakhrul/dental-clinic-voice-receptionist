variable "org_id" {
  description = "Organization number (from infra/bootstrap/foundation.yaml once an organization exists)."
  type        = string
}

variable "folder_id" {
  description = "Number of the dental-ai folder."
  type        = string
}

variable "directory_customer_id" {
  description = "Workspace / Cloud Identity customer ID (Cxxxxxxxx) for iam.allowedPolicyMemberDomains."
  type        = string
}

variable "ops_project_id" {
  description = "Ops project ID (Terraform state, quota project; outside every perimeter)."
  type        = string
  default     = "dai-rcpt-ops"
}

variable "ops_project_number" {
  description = "Ops project number, for the ops override of the service allow-list."
  type        = string
}

variable "project_numbers" {
  description = "Project numbers of the environments that get a perimeter."
  type = object({
    dev     = string
    staging = string
    prod    = string
  })
}

variable "admin_groups" {
  description = "Google groups allowed into every perimeter by the admin ingress rule."
  type        = list(string)
}
