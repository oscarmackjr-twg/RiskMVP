# IPRS Terraform Infrastructure

This directory contains Infrastructure as Code (IaC) for deploying the IPRS Portfolio Analytics Platform to AWS.

## Architecture Overview

The infrastructure consists of:

- **VPC**: Multi-AZ VPC with public and private subnets across 2 availability zones
- **Networking**: Internet Gateway, NAT Gateway, and route tables for public/private subnet routing
- **RDS**: Aurora PostgreSQL 15.x cluster with 2 instances for high availability
- **RDS Proxy**: Connection pooling layer between ECS tasks and Aurora
- **ECS**: Fargate cluster running 4 containerized services (marketdata, orchestrator, results, worker)
- **ECR**: Container image repositories for all services
- **ALB**: Application Load Balancer with path-based routing for service discovery

## Path-Based Routing Structure

The ALB provides service discovery via path prefixes:

| Service | Path Prefix | Target Port | Description |
|---------|-------------|-------------|-------------|
| Marketdata | `/mkt/*` | 8001 | Market data snapshot management |
| Orchestrator | `/orch/*` | 8002 | Run creation and task orchestration |
| Results | `/results/*` | 8003 | Result queries and aggregation |

Example usage:
```
http://<alb-dns>/mkt/health
http://<alb-dns>/orch/runs
http://<alb-dns>/results/runs/123/summary
```

Note: API Gateway is deferred to Phase 2+ for advanced API management features (throttling, API keys, caching). ALB path routing is sufficient for MVP.

## Prerequisites

1. **Terraform**: Install Terraform 1.0+ ([download](https://www.terraform.io/downloads))
2. **AWS CLI**: Configure AWS credentials ([setup guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html))
3. **Docker Images**: Build and push Docker images to ECR before deploying ECS services

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

This downloads the AWS provider and prepares the working directory.

### 2. Plan Infrastructure Changes

```bash
terraform plan -var="db_master_password=YourSecurePassword123!"
```

This shows what resources will be created without making any changes. Review the output carefully.

### 3. Apply Infrastructure

```bash
terraform apply -var="db_master_password=YourSecurePassword123!"
```

Type `yes` when prompted to create the resources. This typically takes 10-15 minutes due to RDS cluster creation.

### 4. Get Outputs

```bash
terraform output
```

Key outputs:
- `alb_dns_name`: DNS name for accessing services
- `rds_proxy_endpoint`: Database endpoint for services
- `ecr_repository_urls`: ECR repositories for pushing Docker images
- `database_url`: Full PostgreSQL connection string (sensitive)

To view sensitive outputs:
```bash
terraform output database_url
```

### 5. Destroy Infrastructure

```bash
terraform destroy -var="db_master_password=YourSecurePassword123!"
```

Type `yes` when prompted. This removes all resources and stops billing.

## Configuration Variables

Variables are defined in `variables.tf`. Override defaults by:

1. **Command-line flags**:
   ```bash
   terraform apply -var="environment=prod" -var="db_master_password=..."
   ```

2. **terraform.tfvars file** (recommended for multiple variables):
   ```hcl
   aws_region         = "us-west-2"
   environment        = "prod"
   project_name       = "iprs"
   vpc_cidr           = "10.0.0.0/16"
   db_master_password = "YourSecurePassword123!"
   ```

3. **Environment variables**:
   ```bash
   export TF_VAR_db_master_password="YourSecurePassword123!"
   terraform apply
   ```

### Key Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region for all resources |
| `environment` | `dev` | Environment name (dev, staging, prod) |
| `project_name` | `iprs` | Project name prefix for all resources |
| `vpc_cidr` | `10.0.0.0/16` | CIDR block for VPC |
| `availability_zones` | `["us-east-1a", "us-east-1b"]` | AZs for multi-AZ deployment |
| `db_master_password` | (required) | Master password for Aurora cluster |

## State Management

Currently using **local state** stored in `terraform.tfstate`. This is suitable for solo development.

For team environments, migrate to **remote state** in S3:

1. Create S3 bucket and DynamoDB table for state locking:
   ```bash
   aws s3 mb s3://iprs-terraform-state
   aws dynamodb create-table \
     --table-name iprs-terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

2. Add backend configuration to `main.tf`:
   ```hcl
   terraform {
     backend "s3" {
       bucket         = "iprs-terraform-state"
       key            = "terraform.tfstate"
       region         = "us-east-1"
       dynamodb_table = "iprs-terraform-locks"
       encrypt        = true
     }
   }
   ```

3. Migrate existing state:
   ```bash
   terraform init -migrate-state
   ```

## Cost Optimization

For development environments:

1. **RDS**: Using `db.t3.medium` instances (cost-effective)
2. **ECS**: Fargate tasks with minimal CPU/memory (256 CPU, 512 MB)
3. **NAT Gateway**: Single NAT gateway (multi-AZ NAT would increase cost)
4. **Aurora**: 7-day backup retention (reduce for dev)

For production, consider:
- Larger RDS instance classes
- Multi-NAT gateway for higher availability
- Auto-scaling for ECS services
- Aurora serverless v2 for variable workloads

## Security

- **VPC**: Private subnets for compute and data layers
- **RDS**: Not publicly accessible, only accessible from ECS security group
- **RDS Proxy**: Connection pooling prevents connection exhaustion attacks
- **Secrets Manager**: Database credentials stored securely
- **IAM**: Least-privilege roles for ECS tasks
- **Security Groups**: Restricted ingress/egress rules

For production:
- Enable ALB HTTPS listener with ACM certificate
- Enable RDS encryption at rest
- Enable VPC Flow Logs
- Enable AWS CloudTrail for audit logging
- Implement WAF rules on ALB

## Deployment Workflow

1. **Build Docker images** (see Docker documentation)
2. **Push images to ECR**:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iprs-marketdata:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iprs-orchestrator:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iprs-results:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/iprs-worker:latest
   ```
3. **Run database migrations**:
   ```bash
   psql $DATABASE_URL -f sql/001_mvp_core.sql
   ```
4. **Verify services** via ALB DNS name

## Troubleshooting

### ECS tasks failing to start

Check CloudWatch Logs:
```bash
aws logs tail /ecs/iprs-dev --follow
```

Common issues:
- Missing Docker images in ECR
- Incorrect DATABASE_URL in task definition
- Security group blocking traffic

### Cannot connect to RDS

Verify:
- ECS tasks are in private subnets
- Security group allows port 5432 from ECS security group
- RDS Proxy endpoint is accessible

### ALB health checks failing

Check:
- Service has `/health` endpoint
- Target group health check settings
- Security group allows ALB to reach ECS tasks on service ports

## Module Structure

| File | Purpose |
|------|---------|
| `main.tf` | Root configuration and AWS provider |
| `variables.tf` | Input variables and defaults |
| `outputs.tf` | Output values (endpoints, IDs) |
| `vpc.tf` | VPC, subnets, NAT, security groups |
| `rds.tf` | Aurora PostgreSQL cluster and RDS Proxy |
| `ecs.tf` | ECS cluster, task definitions, services, ALB |
| `ecr.tf` | ECR repositories for Docker images |
| `.gitignore` | Exclude state files and sensitive data |

## Next Steps

After infrastructure is provisioned:

1. **CI/CD Pipeline**: Automate Docker builds and deployments (Phase 1 Plan 05)
2. **Monitoring**: Set up CloudWatch dashboards and alarms
3. **Auto-Scaling**: Configure ECS service auto-scaling policies
4. **DNS**: Create Route 53 hosted zone and CNAME for ALB
5. **HTTPS**: Request ACM certificate and update ALB listener

## Support

For issues or questions about the infrastructure:
- Review Terraform plan output carefully before applying
- Check AWS console for resource status
- Consult `.planning/phases/01-foundation-infrastructure/01-04-SUMMARY.md` for implementation details
