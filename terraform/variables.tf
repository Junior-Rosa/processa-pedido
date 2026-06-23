variable "cluster_name" {
  description = "Nome do cluster k3d"
  type        = string
  default     = "processador-pedidos"
}

variable "namespace" {
  description = "Namespace k8s usado pela aplicação"
  type        = string
  default     = "processador-pedidos"
}

variable "image_name" {
  description = "Tag da imagem Docker da aplicação"
  type        = string
  default     = "pedidos-app:v1"
}

variable "kubeconfig_path" {
  description = "Caminho do kubeconfig usado pelo provider kubectl"
  type        = string
  default     = "~/.kube/config"
}

variable "k8s_manifests_dir" {
  description = "Diretório com os manifests k8s (1 recurso por arquivo)"
  type        = string
  default     = "../k8s"
}
