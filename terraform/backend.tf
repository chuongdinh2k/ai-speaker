terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "ai-speaker-terraform-state"
    key            = "frontend/production/terraform.tfstate"
    region         = "ap-southeast-2"
    dynamodb_table = "ai-speaker-terraform-locks"
    encrypt        = true
  }
}
