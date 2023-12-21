variable "project_id" {
  type        = string
  description = "ID of the Google Project"
}

variable "region" {
  type        = string
  description = "Default Region"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "Default Zone"
  default     = "us-central1-a"
}

variable "cluster_name" {
  type        = string
  description = "Name of server"
}

variable "node_pool" {
    type        = string
    description = "Name of Node Pool"
    default     = "main-node-pool"
}

variable "machine_type" {
  type        = string
  description = "Machine Type"
  default     = "e2-highmem-4" # !!! e2-standard-4 n1-standard-4
}

variable "credentials_json" {
  type        = string
  description = "Credentials JSON file"
  default     = "terraform.json"
}

variable "gpu_type" {
  default     = "nvidia-tesla-t4"
  description = "the GPU accelerator type"
}

variable "gpu_driver_version" {
  default = "DEFAULT"
  description = "the NVIDIA driver version to install"
}