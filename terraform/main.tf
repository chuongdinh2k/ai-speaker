provider "aws" {
  region = var.region
}

module "frontend" {
  source = "./modules/frontend"

  project_name = var.project_name
  environment  = var.environment
  region       = var.region
}
