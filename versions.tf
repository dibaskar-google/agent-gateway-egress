terraform {
  required_version = ">= 1.12.2"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 8.6.0, < 9.0.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 8.6.0, < 9.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

