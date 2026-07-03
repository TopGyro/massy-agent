variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "massy-agent"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}
