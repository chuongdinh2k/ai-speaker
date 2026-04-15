variable "project_name" {
  description = "Project name used to namespace AWS resource names"
  type        = string
  default     = "ai-speaker"
}

variable "environment" {
  description = "Deployment environment (e.g. production, staging)"
  type        = string
  default     = "production"
}

variable "region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "ap-southeast-2"
}

variable "domain_name" {
  description = "Custom domain for the CloudFront distribution. Leave empty to use the default CloudFront domain."
  type        = string
  default     = ""
}
