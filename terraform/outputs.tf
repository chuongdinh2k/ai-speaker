output "frontend_bucket_name" {
  description = "S3 bucket name for the frontend — use in CI/CD aws s3 sync"
  value       = module.frontend.bucket_name
}

output "frontend_cloudfront_domain" {
  description = "CloudFront domain name — open this in a browser to access the site"
  value       = module.frontend.cloudfront_domain
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID — use in CI/CD cache invalidation"
  value       = module.frontend.cloudfront_distribution_id
}

output "frontend_acm_certificate_validation_records" {
  description = "Add these CNAME records in Namecheap DNS to validate the ACM certificate"
  value       = module.frontend.acm_certificate_validation_records
}
