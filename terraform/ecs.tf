# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project_name}-cluster-${var.environment}"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-ecs-logs-${var.environment}"
  }
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-execution-${var.environment}"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Tasks (application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-task-${var.environment}"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_ssm" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# Data source for current region
data "aws_region" "current" {}

# ============================================================
# Task Definitions
# ============================================================

# Task Definition - Marketdata Service
resource "aws_ecs_task_definition" "marketdata" {
  family                   = "${var.project_name}-marketdata-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "marketdata"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.marketdata.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8001
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "marketdata"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-marketdata-task-${var.environment}"
    Service = "marketdata"
  }
}

# Task Definition - Orchestrator Service
resource "aws_ecs_task_definition" "orchestrator" {
  family                   = "${var.project_name}-orchestrator-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "orchestrator"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.orchestrator.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8002
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "orchestrator"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-orchestrator-task-${var.environment}"
    Service = "orchestrator"
  }
}

# Task Definition - Results Service
resource "aws_ecs_task_definition" "results" {
  family                   = "${var.project_name}-results-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "results"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.results.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8003
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "results"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-results-task-${var.environment}"
    Service = "results"
  }
}

# Task Definition - Worker
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project_name}-worker-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.worker.name}:latest"
      essential = true
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        },
        {
          name  = "WORKER_ID"
          value = "worker-fargate-1"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-worker-task-${var.environment}"
    Service = "worker"
  }
}

# Task Definition - Portfolio Service
resource "aws_ecs_task_definition" "portfolio" {
  family                   = "${var.project_name}-portfolio-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "portfolio"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.portfolio.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8005
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "portfolio"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-portfolio-task-${var.environment}"
    Service = "portfolio"
  }
}

# Task Definition - Risk Service
resource "aws_ecs_task_definition" "risk" {
  family                   = "${var.project_name}-risk-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "risk"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.risk.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8006
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "risk"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-risk-task-${var.environment}"
    Service = "risk"
  }
}

# Task Definition - Regulatory Service
resource "aws_ecs_task_definition" "regulatory" {
  family                   = "${var.project_name}-regulatory-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "regulatory"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.regulatory.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8007
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "regulatory"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-regulatory-task-${var.environment}"
    Service = "regulatory"
  }
}

# Task Definition - Ingestion Service
resource "aws_ecs_task_definition" "ingestion" {
  family                   = "${var.project_name}-ingestion-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "ingestion"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.ingestion.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8008
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_master_username}:${var.db_master_password}@${aws_db_proxy.main.endpoint}:5432/${var.db_name}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ingestion"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-ingestion-task-${var.environment}"
    Service = "ingestion"
  }
}

# Task Definition - Frontend (nginx + React SPA)
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${aws_ecr_repository.frontend.name}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])

  tags = {
    Name    = "${var.project_name}-frontend-task-${var.environment}"
    Service = "frontend"
  }
}

# ============================================================
# Application Load Balancer — routes all traffic to frontend
# ============================================================

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name = "${var.project_name}-alb-${var.environment}"
  }
}

# Single target group — frontend nginx handles all path-based routing
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-fe-tg-${var.environment}"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-frontend-tg-${var.environment}"
    Service = "frontend"
  }
}

# ALB Listener — forward everything to frontend
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  tags = {
    Name = "${var.project_name}-alb-listener-http-${var.environment}"
  }
}

# ============================================================
# ECS Services — backend (internal, Cloud Map only)
# ============================================================

# ECS Service - Marketdata
resource "aws_ecs_service" "marketdata" {
  name                   = "${var.project_name}-marketdata-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.marketdata.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.marketdata.arn
  }

  tags = {
    Name    = "${var.project_name}-marketdata-service-${var.environment}"
    Service = "marketdata"
  }
}

# ECS Service - Orchestrator
resource "aws_ecs_service" "orchestrator" {
  name                   = "${var.project_name}-orchestrator-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.orchestrator.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.orchestrator.arn
  }

  tags = {
    Name    = "${var.project_name}-orchestrator-service-${var.environment}"
    Service = "orchestrator"
  }
}

# ECS Service - Results
resource "aws_ecs_service" "results" {
  name                   = "${var.project_name}-results-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.results.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.results.arn
  }

  tags = {
    Name    = "${var.project_name}-results-service-${var.environment}"
    Service = "results"
  }
}

# ECS Service - Worker (no port mapping, no service registry needed for discovery
# but registered for visibility in Cloud Map)
resource "aws_ecs_service" "worker" {
  name                   = "${var.project_name}-worker-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.worker.arn
  desired_count          = 1
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.worker.arn
  }

  tags = {
    Name    = "${var.project_name}-worker-service-${var.environment}"
    Service = "worker"
  }
}

# ECS Service - Portfolio
resource "aws_ecs_service" "portfolio" {
  name                   = "${var.project_name}-portfolio-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.portfolio.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.portfolio.arn
  }

  tags = {
    Name    = "${var.project_name}-portfolio-service-${var.environment}"
    Service = "portfolio"
  }
}

# ECS Service - Risk
resource "aws_ecs_service" "risk" {
  name                   = "${var.project_name}-risk-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.risk.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.risk.arn
  }

  tags = {
    Name    = "${var.project_name}-risk-service-${var.environment}"
    Service = "risk"
  }
}

# ECS Service - Regulatory
resource "aws_ecs_service" "regulatory" {
  name                   = "${var.project_name}-regulatory-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.regulatory.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.regulatory.arn
  }

  tags = {
    Name    = "${var.project_name}-regulatory-service-${var.environment}"
    Service = "regulatory"
  }
}

# ECS Service - Ingestion
resource "aws_ecs_service" "ingestion" {
  name                   = "${var.project_name}-ingestion-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.ingestion.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.ingestion.arn
  }

  tags = {
    Name    = "${var.project_name}-ingestion-service-${var.environment}"
    Service = "ingestion"
  }
}

# ============================================================
# ECS Service — Frontend (ALB-facing)
# ============================================================

resource "aws_ecs_service" "frontend" {
  name                   = "${var.project_name}-frontend-${var.environment}"
  cluster                = aws_ecs_cluster.main.id
  task_definition        = aws_ecs_task_definition.frontend.arn
  desired_count          = 2
  launch_type            = "FARGATE"
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-frontend-service-${var.environment}"
    Service = "frontend"
  }
}
