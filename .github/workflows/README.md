# CI/CD Workflows

This directory contains GitHub Actions workflows for continuous integration and deployment of the IPRS platform.

## Workflows

### 1. ci.yml - Continuous Integration

**Triggers:** Push to any branch, pull requests to main

**Jobs:**

- **Lint** - Validates Python code quality
  - Runs `ruff check .` for style and correctness
  - Runs `mypy` for type checking (optional, may fail without strict typing)

- **Test** - Runs test suite
  - Executes pytest against compute/tests/
  - Validates golden pricer outputs and worker registry

- **Build** - Validates Docker images
  - Builds all 4 service images (marketdata, orchestrator, results, worker)
  - Tags with commit SHA for traceability
  - Does NOT push to ECR (validation only)

**Required checks:** All jobs must pass for PR merge approval.

### 2. deploy.yml - Deployment to AWS ECS

**Triggers:** Push to main branch (after CI passes), manual workflow dispatch

**Jobs:**

- **Build and Push to ECR**
  - Authenticates to AWS using OIDC (role assumption)
  - Builds and tags Docker images with commit SHA and "latest"
  - Pushes to Amazon ECR
  - Uses matrix strategy for all 4 services + worker

- **Deploy to ECS**
  - Downloads current task definitions from ECS
  - Updates container image tags to new commit SHA
  - Registers new task definition revision
  - Forces new deployment to ECS Fargate services
  - Waits for deployment to stabilize (10 minute timeout)
  - Verifies deployment status

**Deployment strategy:** Blue/green via ECS task definition revision. Old tasks drain, new tasks start.

## Required GitHub Secrets

Configure in repository **Settings > Secrets and variables > Actions**:

| Secret | Description | Example |
|--------|-------------|---------|
| `AWS_ROLE_ARN` | IAM role ARN for OIDC authentication | `arn:aws:iam::123456789012:role/github-actions-iprs` |
| `AWS_REGION` | AWS region for ECS and ECR | `us-east-1` |
| `ECR_REGISTRY` | ECR registry URL | `123456789012.dkr.ecr.us-east-1.amazonaws.com` |

### Setting up AWS_ROLE_ARN (OIDC)

1. Create IAM role with trust policy for GitHub OIDC provider:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::123456789012:identity-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
           },
           "StringLike": {
             "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
           }
         }
       }
     ]
   }
   ```

2. Attach permissions policy to role (see IAM Role Permissions below)

3. Copy role ARN to GitHub secret `AWS_ROLE_ARN`

## IAM Role Permissions

The GitHub Actions role needs the following AWS permissions:

**ECR (Container Registry):**
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:PutImage`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`

**ECS (Container Orchestration):**
- `ecs:DescribeTaskDefinition`
- `ecs:RegisterTaskDefinition`
- `ecs:UpdateService`
- `ecs:DescribeServices`

**IAM (for passing roles to ECS tasks):**
- `iam:PassRole` (for task execution and task roles)

### Example IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService",
        "ecs:DescribeServices"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::123456789012:role/iprs-ecs-task-execution-prod",
        "arn:aws:iam::123456789012:role/iprs-ecs-task-prod"
      ]
    }
  ]
}
```

## Local Testing

Run CI checks locally before pushing:

```bash
# Lint
pip install ruff mypy
ruff check .
mypy compute/ services/ --ignore-missing-imports

# Test
pip install -e .
pip install pytest fastapi
pytest compute/tests/ -v

# Build (validate Dockerfiles)
docker build -f docker/Dockerfile.marketdata -t iprs-marketdata:local .
docker build -f docker/Dockerfile.orchestrator -t iprs-orchestrator:local .
docker build -f docker/Dockerfile.results -t iprs-results:local .
docker build -f docker/Dockerfile.worker -t iprs-worker:local .
```

## Workflow Execution

### Automatic Triggers

1. **On every push to any branch:** CI workflow runs (lint, test, build)
2. **On pull request to main:** CI workflow runs
3. **On push to main:** CI workflow runs, then deploy workflow runs (if CI passes)

### Manual Triggers

You can manually trigger the deploy workflow from GitHub Actions UI:
1. Go to Actions tab
2. Select "Deploy to AWS ECS" workflow
3. Click "Run workflow"
4. Select branch (usually main)

## Troubleshooting

### CI Failures

**Lint errors:**
```bash
# Check locally
ruff check .

# Fix automatically where possible
ruff check . --fix
```

**Test failures:**
```bash
# Run tests locally with verbose output
pytest compute/tests/ -v

# Run specific test
pytest compute/tests/golden/test_bond_golden.py -v
```

**Build failures:**
- Check Docker file syntax
- Verify base image availability
- Check for missing dependencies in requirements.txt

### Deployment Failures

**Authentication errors:**
- Verify `AWS_ROLE_ARN` secret is correct
- Check OIDC trust policy allows your repository
- Ensure role has required permissions

**ECR push failures:**
- Verify `ECR_REGISTRY` secret matches actual registry URL
- Check ECR repository exists (created by Terraform)
- Verify role has ECR push permissions

**ECS deployment failures:**
- Check ECS service exists and is running
- Verify task definition family names match Terraform output
- Check CloudWatch logs for container startup errors
- Verify RDS database is accessible from ECS tasks

**Deployment timeout:**
- Check ECS service events in AWS Console
- Verify health checks are passing
- Check application logs in CloudWatch
- May need to increase wait timeout if first deployment

## Service Names and Ports

| Service | ECS Service Name | Task Family | Port |
|---------|------------------|-------------|------|
| Marketdata | iprs-marketdata-prod | iprs-marketdata-prod | 8001 |
| Orchestrator | iprs-orchestrator-prod | iprs-orchestrator-prod | 8002 |
| Results | iprs-results-prod | iprs-results-prod | 8003 |
| Worker | iprs-worker-prod | iprs-worker-prod | N/A |

## Monitoring Deployments

After deployment, verify services are healthy:

```bash
# Check service status
aws ecs describe-services \
  --cluster iprs-cluster-prod \
  --services iprs-marketdata-prod \
  --query 'services[0].deployments'

# Check running tasks
aws ecs list-tasks \
  --cluster iprs-cluster-prod \
  --service-name iprs-marketdata-prod

# View container logs
aws logs tail /ecs/iprs-prod --follow
```

## Security Best Practices

1. **Use OIDC authentication** (no long-lived credentials)
2. **Principle of least privilege** (role has only required permissions)
3. **Secrets in GitHub Secrets** (never commit credentials)
4. **ECR image scanning** (enabled in Terraform)
5. **Task execution role separation** (execution vs task roles)
6. **VPC security groups** (restrict network access)

## Related Documentation

- **Terraform infrastructure:** `terraform/README.md`
- **Docker images:** `docker/README.md` (if exists)
- **ECS architecture:** `terraform/ecs.tf`
- **ECR repositories:** `terraform/ecr.tf`
