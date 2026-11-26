# State lives in the ops bucket created by P0-05 runbook Part B (deferred: no billing account yet, DECISIONS #294).
# Until it exists, validate with: terraform init -backend=false && terraform validate
terraform {
  backend "gcs" {
    bucket = "dai-rcpt-ops-tfstate"
    prefix = "org/"
  }
}
