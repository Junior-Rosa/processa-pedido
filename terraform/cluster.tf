resource "null_resource" "k3d_cluster" {
  triggers = {
    cluster_name = var.cluster_name
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      if k3d cluster list | grep -q "^${var.cluster_name} "; then
        echo "Cluster ${var.cluster_name} já existe, pulando criação."
      else
        k3d cluster create ${var.cluster_name} \
          --servers 1 --agents 2 \
          --port "5000:30000@loadbalancer" \
          --port "3000:30001@loadbalancer" \
          --port "15672:30002@loadbalancer" \
          --port "9090:30003@loadbalancer" \
          --port "3001:30004@loadbalancer"
      fi
      k3d kubeconfig merge ${var.cluster_name} --kubeconfig-switch-context
      kubectl create namespace ${var.namespace} --dry-run=client -o yaml | kubectl apply -f -
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = "k3d cluster delete ${self.triggers.cluster_name} || true"
  }
}
