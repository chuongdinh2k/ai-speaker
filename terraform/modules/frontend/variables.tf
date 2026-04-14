variable "project_name" {
  description = "Project name used to namespace AWS resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. production, staging)"
  type        = string
}

variable "region" {
  description = "AWS region (used for reference only — provider is configured at root)"
  type        = string
}
