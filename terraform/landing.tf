# ─── S3 Landing Page ─────────────────────────────────────────────────────────
# Separate bucket from the data bucket — public static site hosting

resource "aws_s3_bucket" "landing" {
  bucket = "${var.project_name}-landing-${var.environment}"
}

resource "aws_s3_bucket_website_configuration" "landing" {
  bucket = aws_s3_bucket.landing.id
  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "landing" {
  bucket                  = aws_s3_bucket.landing.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "landing" {
  bucket = aws_s3_bucket.landing.id

  depends_on = [aws_s3_bucket_public_access_block.landing]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.landing.arn}/*"
    }]
  })
}

resource "aws_s3_object" "landing_page" {
  bucket       = aws_s3_bucket.landing.id
  key          = "index.html"
  source       = "${path.module}/../landing/index.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../landing/index.html")
}

output "landing_page_url" {
  value       = "http://${aws_s3_bucket.landing.bucket}.s3-website-${var.aws_region}.amazonaws.com"
  description = "Public URL of the landing page"
}
