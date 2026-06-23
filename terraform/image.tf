resource "null_resource" "app_image" {
  depends_on = [null_resource.k3d_cluster]

  triggers = {
    dockerfile_hash = filesha256("${path.module}/../Dockerfile")
    pyproject_hash  = filesha256("${path.module}/../pyproject.toml")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      docker build -t ${var.image_name} ${path.module}/..
      k3d image import ${var.image_name} -c ${var.cluster_name}
    EOT
  }
}
