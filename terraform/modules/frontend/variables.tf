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

variable "domain_name" {
  description = "Custom domain for the CloudFront distribution (e.g. stephendinh.best). Leave empty to use the default CloudFront domain."
  type        = string
  default     = ""
}

