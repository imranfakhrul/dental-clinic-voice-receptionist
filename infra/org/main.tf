# P0-06 guardrails: org policies, access policy and VPC-SC perimeters.
# Allowed APIs come from allowed_services.yaml (single source of truth). Evidence: docs/compliance/hipaa-controls.md.

locals {
  allowed = yamldecode(file("${path.module}/allowed_services.yaml"))

  # yamldecode reads YAML 1.2, so yes/no stay strings; accept both spellings.
  truthy = ["yes", "true"]

  # Only services that restrictServiceUsage supports can appear in its allow-list.
  allowed_apis = sort([
    for s in local.allowed.services : s.api if contains(local.truthy, lower(tostring(s.restrict_supported)))
  ])
  ops_allowed_apis = sort([
    for s in local.allowed.ops_services : s.api if contains(local.truthy, lower(tostring(s.restrict_supported)))
  ])
  perimeter_apis = sort([
    for s in local.allowed.services : s.api if contains(local.truthy, lower(tostring(s.vpcsc_restricted)))
  ])

  org     = "organizations/${var.org_id}"
  folder  = "folders/${var.folder_id}"
  members = [for g in var.admin_groups : "group:${g}"]

  boolean_constraints = [
    "iam.disableServiceAccountKeyCreation",
    "iam.automaticIamGrantsForDefaultServiceAccounts",
    "storage.uniformBucketLevelAccess",
    "storage.publicAccessPrevention",
    "sql.restrictPublicIp",
  ]
}

# --- Organization level --------------------------------------------------------------------------

# Gemini Developer API (AI Studio) is never allowed anywhere (plan §3.3).
resource "google_org_policy_policy" "org_deny_gemini_developer_api" {
  name   = "${local.org}/policies/gcp.restrictServiceUsage"
  parent = local.org
  spec {
    rules {
      values {
        denied_values = ["generativelanguage.googleapis.com"]
      }
    }
  }
}

resource "google_org_policy_policy" "org_us_locations" {
  name   = "${local.org}/policies/gcp.resourceLocations"
  parent = local.org
  spec {
    rules {
      values {
        allowed_values = ["in:us-locations"]
      }
    }
  }
}

resource "google_org_policy_policy" "org_boolean" {
  for_each = toset(local.boolean_constraints)
  name     = "${local.org}/policies/${each.value}"
  parent   = local.org
  spec {
    rules {
      enforce = "TRUE"
    }
  }
}

resource "google_org_policy_policy" "org_allowed_member_domains" {
  name   = "${local.org}/policies/iam.allowedPolicyMemberDomains"
  parent = local.org
  spec {
    rules {
      values {
        allowed_values = [var.directory_customer_id]
      }
    }
  }
}

resource "google_org_policy_policy" "org_no_vm_external_ip" {
  name   = "${local.org}/policies/compute.vmExternalIpAccess"
  parent = local.org
  spec {
    rules {
      deny_all = "TRUE"
    }
  }
}

# --- Folder dental-ai: service allow-list; ops gets its own short list -----------------------------

resource "google_org_policy_policy" "folder_allowed_services" {
  name   = "${local.folder}/policies/gcp.restrictServiceUsage"
  parent = local.folder
  spec {
    rules {
      values {
        allowed_values = local.allowed_apis
      }
    }
  }
  depends_on = [google_org_policy_policy.org_deny_gemini_developer_api]
}

resource "google_org_policy_policy" "ops_allowed_services" {
  name   = "projects/${var.ops_project_number}/policies/gcp.restrictServiceUsage"
  parent = "projects/${var.ops_project_number}"
  spec {
    rules {
      values {
        allowed_values = local.ops_allowed_apis
      }
    }
  }
  depends_on = [google_org_policy_policy.folder_allowed_services]
}

# --- VPC Service Controls ------------------------------------------------------------------------
# Only one org-level access policy can exist. If one already exists, import it instead of creating it:
#   terraform import google_access_context_manager_access_policy.org accessPolicies/<id>

resource "google_access_context_manager_access_policy" "org" {
  parent = local.org
  title  = "dental-ai"
}

locals {
  policy_name = "accessPolicies/${google_access_context_manager_access_policy.org.name}"
}

# prod: enforced now.
resource "google_access_context_manager_service_perimeter" "prod" {
  parent = local.policy_name
  name   = "${local.policy_name}/servicePerimeters/dai_prod"
  title  = "dai_prod"

  status {
    resources           = ["projects/${var.project_numbers.prod}"]
    restricted_services = local.perimeter_apis

    ingress_policies {
      ingress_from {
        identities = local.members
        sources {
          access_level = "*"
        }
      }
      ingress_to {
        resources = ["*"]
        operations {
          service_name = "*"
        }
      }
    }
  }
}

# dev and staging: dry-run until P1-02 has reviewed the dry-run logs.
resource "google_access_context_manager_service_perimeter" "dry_run" {
  for_each = {
    dev     = var.project_numbers.dev
    staging = var.project_numbers.staging
  }
  parent                    = local.policy_name
  name                      = "${local.policy_name}/servicePerimeters/dai_${each.key}"
  title                     = "dai_${each.key}"
  use_explicit_dry_run_spec = true

  spec {
    resources           = ["projects/${each.value}"]
    restricted_services = local.perimeter_apis

    ingress_policies {
      ingress_from {
        identities = local.members
        sources {
          access_level = "*"
        }
      }
      ingress_to {
        resources = ["*"]
        operations {
          service_name = "*"
        }
      }
    }
  }
}
