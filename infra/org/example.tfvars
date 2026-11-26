# EXAMPLE values for terraform validate/plan practice. The org, folder and customer IDs are fake:
# there is no organization yet (DECISIONS #293). Project numbers are the real ones from foundation.yaml.
# Copy to terraform.tfvars and fill in real IDs once the organization exists.
org_id                = "000000000000"
folder_id             = "000000000000"
directory_customer_id = "C00000000"
ops_project_id        = "dai-rcpt-ops"
ops_project_number    = "428568892795"
project_numbers = {
  dev     = "583464999786"
  staging = "445637737319"
  prod    = "763436157077"
}
admin_groups = ["gcp-org-admins@example.com", "gcp-security-admins@example.com"]
