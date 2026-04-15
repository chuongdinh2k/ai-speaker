output "bucket_name" {
  description = "Name of the S3 bucket holding frontend assets"
  value       = aws_s3_bucket.frontend.id
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name (e.g. abc123.cloudfront.net)"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — used by CI/CD cache invalidation"
  value       = aws_cloudfront_distribution.frontend.id
}

output "acm_certificate_validation_records" {
  description = "DNS CNAME records to add in Namecheap to validate the ACM certificate"
  value = var.domain_name != "" ? {
    for dvo in aws_acm_certificate.frontend[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  } : {}
}
