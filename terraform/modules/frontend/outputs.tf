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
