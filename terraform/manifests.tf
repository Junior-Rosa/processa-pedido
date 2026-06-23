# Cada arquivo em k8s/ contém exatamente um recurso (split feito deliberadamente)
# para que o for_each abaixo funcione sem parsing de YAML multi-documento.
resource "kubectl_manifest" "app" {
  for_each = fileset(var.k8s_manifests_dir, "*.yaml")

  yaml_body = file("${var.k8s_manifests_dir}/${each.value}")

  depends_on = [null_resource.app_image]
}
