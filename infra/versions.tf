# Versiones de Terraform y del proveedor de AWS.
# El proveedor es el "traductor" entre los archivos .tf y la API de AWS.

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region

  # Todas las piezas quedan etiquetadas: así se encuentran fácil en la consola y en la
  # factura de AWS.
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}
