terraform {
  required_version = ">= 1.5.0"

  required_providers {
    null    = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    kubectl = {
      source  = "alekc/kubectl"
      version = "~> 2.0"
    }
  }
}

provider "kubectl" {
  config_path    = pathexpand(var.kubeconfig_path)
  config_context = "k3d-${var.cluster_name}"
}
