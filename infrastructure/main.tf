###############################################################################
# ApplyPilot — AWS Free Tier Infrastructure
# Deploys: VPC, EC2 t2.micro, RDS t3.micro (Postgres), ElastiCache t2.micro,
#          ECR repos, S3 + CloudFront (frontend), SES email identity
###############################################################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # Store state in S3 (free); create the bucket manually once, then uncomment:
  # backend "s3" {
  #   bucket = "applypilot-tfstate"
  #   key    = "prod/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

###############################################################################
# Variables
###############################################################################

variable "aws_region"   { default = "us-east-1" }
variable "app_name"     { default = "applypilot" }
variable "db_password"  { sensitive = true }
variable "jwt_secret"   { sensitive = true }
variable "domain_name"  { default = "" }   # optional: your custom domain

locals {
  tags = { Project = var.app_name, ManagedBy = "terraform" }
}

###############################################################################
# VPC
###############################################################################

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = merge(local.tags, { Name = "${var.app_name}-vpc" })
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags = merge(local.tags, { Name = "${var.app_name}-public-a" })
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"
  map_public_ip_on_launch = true
  tags = merge(local.tags, { Name = "${var.app_name}-public-b" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.tags, { Name = "${var.app_name}-igw" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = merge(local.tags, { Name = "${var.app_name}-rt-public" })
}

resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

###############################################################################
# Security Groups
###############################################################################

resource "aws_security_group" "ec2" {
  name   = "${var.app_name}-ec2-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # tighten to your IP in production
  }
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 8001
    to_port     = 8001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags
}

resource "aws_security_group" "rds" {
  name   = "${var.app_name}-rds-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }
  tags = local.tags
}

resource "aws_security_group" "redis" {
  name   = "${var.app_name}-redis-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }
  tags = local.tags
}

###############################################################################
# RDS PostgreSQL (db.t3.micro — free tier 750h/month)
###############################################################################

resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-db-subnet-group"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]
  tags       = local.tags
}

resource "aws_db_instance" "postgres" {
  identifier        = "${var.app_name}-db"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.micro"   # free tier
  allocated_storage = 20              # free tier: 20 GB
  storage_type      = "gp2"

  db_name  = "jobassistant"
  username = "applypilot"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  backup_retention_period = 0
  tags = local.tags
}

###############################################################################
# ElastiCache Redis (cache.t2.micro — free tier 750h/month)
###############################################################################

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.app_name}-redis-subnet"
  subnet_ids = [aws_subnet.public_a.id]
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.app_name}-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]
  tags                 = local.tags
}

###############################################################################
# EC2 (t2.micro — free tier 750h/month)
###############################################################################

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_iam_role" "ec2_role" {
  name = "${var.app_name}-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "ses_send" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSESFullAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.app_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"   # free tier
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  key_name               = "applypilot-key"

  root_block_device {
    volume_size = 20   # free tier: 30 GB EBS gp2 total
    volume_type = "gp2"
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    app_name      = var.app_name
    aws_region    = var.aws_region
    db_url        = "postgres://applypilot:${var.db_password}@${aws_db_instance.postgres.address}:5432/jobassistant"
    redis_url     = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379"
    jwt_secret    = var.jwt_secret
    ecr_registry  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
  }))

  tags = merge(local.tags, { Name = "${var.app_name}-app" })
}

data "aws_caller_identity" "current" {}

###############################################################################
# ECR Repositories
###############################################################################

resource "aws_ecr_repository" "backend" {
  name                 = "${var.app_name}/backend"
  image_tag_mutability = "MUTABLE"
  tags                 = local.tags
}

resource "aws_ecr_repository" "workers" {
  name                 = "${var.app_name}/workers"
  image_tag_mutability = "MUTABLE"
  tags                 = local.tags
}

resource "aws_ecr_repository" "ml_service" {
  name                 = "${var.app_name}/ml-service"
  image_tag_mutability = "MUTABLE"
  tags                 = local.tags
}

###############################################################################
# S3 + CloudFront (Next.js static frontend)
###############################################################################

resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.app_name}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = local.tags
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.app_name}-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"   # US + EU only (cheapest)

  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # SPA: redirect 404/403 to index.html
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.tags
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.frontend.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
        }
      }
    }]
  })
}

###############################################################################
# SES — email identity (verify your domain or single address)
###############################################################################

resource "aws_ses_email_identity" "noreply" {
  email = "noreply@${var.domain_name != "" ? var.domain_name : "example.com"}"
}

###############################################################################
# Outputs
###############################################################################

output "ec2_public_ip" {
  value       = aws_instance.app.public_ip
  description = "SSH and API endpoint IP"
}

output "rds_endpoint" {
  value       = aws_db_instance.postgres.address
  description = "PostgreSQL host"
}

output "redis_endpoint" {
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  description = "Redis host"
}

output "cloudfront_domain" {
  value       = aws_cloudfront_distribution.frontend.domain_name
  description = "Frontend URL (use this until you attach a custom domain)"
}

output "ecr_registry" {
  value = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}
