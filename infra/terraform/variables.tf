variable "aws_region" {
  type        = string
  description = "AWS region to deploy into."
  default     = "us-east-1"
}

variable "service_name" {
  type    = string
  default = "stocksense-api"
}

variable "artifact_bucket_name" {
  type        = string
  description = "Globally-unique S3 bucket name for model artefacts."
}

variable "ecr_repo_name" {
  type    = string
  default = "stocksense-api"
}

variable "task_cpu" {
  type    = number
  default = 512
}

variable "task_memory" {
  type    = number
  default = 1024
}

variable "subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs for the Fargate service."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups allowing ingress to port 8001."
}

variable "tags" {
  type    = map(string)
  default = {
    Project   = "stocksense"
    ManagedBy = "terraform"
  }
}
