# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

# Security Group Outputs
output "alb_security_group_id" {
  description = "ID of ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_tasks_security_group_id" {
  description = "ID of ECS tasks security group"
  value       = aws_security_group.ecs_tasks.id
}

output "rds_security_group_id" {
  description = "ID of RDS security group"
  value       = aws_security_group.rds.id
}

# RDS Outputs
output "rds_cluster_endpoint" {
  description = "Writer endpoint for Aurora cluster"
  value       = aws_rds_cluster.main.endpoint
}

output "rds_cluster_reader_endpoint" {
  description = "Reader endpoint for Aurora cluster"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "rds_proxy_endpoint" {
  description = "RDS Proxy endpoint (use this for DATABASE_URL)"
  value       = aws_db_proxy.main.endpoint
}

output "database_url" {
  description = "PostgreSQL connection string via RDS Proxy"
  value       = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
  sensitive   = true
}

# ECS Outputs
output "ecs_cluster_id" {
  description = "ID of ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Name of ECS cluster"
  value       = aws_ecs_cluster.main.name
}

# ECR Outputs
output "ecr_repository_urls" {
  description = "URLs of ECR repositories"
  value = {
    marketdata   = aws_ecr_repository.marketdata.repository_url
    orchestrator = aws_ecr_repository.orchestrator.repository_url
    results      = aws_ecr_repository.results.repository_url
    worker       = aws_ecr_repository.worker.repository_url
    portfolio    = aws_ecr_repository.portfolio.repository_url
    risk         = aws_ecr_repository.risk.repository_url
    regulatory   = aws_ecr_repository.regulatory.repository_url
    ingestion    = aws_ecr_repository.ingestion.repository_url
    frontend     = aws_ecr_repository.frontend.repository_url
  }
}

# ALB Outputs
output "alb_dns_name" {
  description = "DNS name of Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of Application Load Balancer"
  value       = aws_lb.main.zone_id
}
