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

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# Data source for current region
data "aws_region" "current" {}

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

# Application Load Balancer
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

# Target Group - Marketdata
resource "aws_lb_target_group" "marketdata" {
  name        = "${var.project_name}-mkt-tg-${var.environment}"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-marketdata-tg-${var.environment}"
    Service = "marketdata"
  }
}

# Target Group - Orchestrator
resource "aws_lb_target_group" "orchestrator" {
  name        = "${var.project_name}-orch-tg-${var.environment}"
  port        = 8002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-orchestrator-tg-${var.environment}"
    Service = "orchestrator"
  }
}

# Target Group - Results
resource "aws_lb_target_group" "results" {
  name        = "${var.project_name}-res-tg-${var.environment}"
  port        = 8003
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-results-tg-${var.environment}"
    Service = "results"
  }
}

# ALB Listener (HTTP - for dev, redirect to HTTPS in prod)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "404: Not Found"
      status_code  = "404"
    }
  }

  tags = {
    Name = "${var.project_name}-alb-listener-http-${var.environment}"
  }
}

# ALB Listener Rule - Marketdata (path-based routing)
resource "aws_lb_listener_rule" "marketdata" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.marketdata.arn
  }

  condition {
    path_pattern {
      values = ["/mkt/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-marketdata-${var.environment}"
    Service = "marketdata"
  }
}

# ALB Listener Rule - Orchestrator (path-based routing)
resource "aws_lb_listener_rule" "orchestrator" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.orchestrator.arn
  }

  condition {
    path_pattern {
      values = ["/orch/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-orchestrator-${var.environment}"
    Service = "orchestrator"
  }
}

# ALB Listener Rule - Results (path-based routing)
resource "aws_lb_listener_rule" "results" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 300

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.results.arn
  }

  condition {
    path_pattern {
      values = ["/results/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-results-${var.environment}"
    Service = "results"
  }
}

# ECS Service - Marketdata
resource "aws_ecs_service" "marketdata" {
  name            = "${var.project_name}-marketdata-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.marketdata.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.marketdata.arn
    container_name   = "marketdata"
    container_port   = 8001
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-marketdata-service-${var.environment}"
    Service = "marketdata"
  }
}

# ECS Service - Orchestrator
resource "aws_ecs_service" "orchestrator" {
  name            = "${var.project_name}-orchestrator-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.orchestrator.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.orchestrator.arn
    container_name   = "orchestrator"
    container_port   = 8002
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-orchestrator-service-${var.environment}"
    Service = "orchestrator"
  }
}

# ECS Service - Results
resource "aws_ecs_service" "results" {
  name            = "${var.project_name}-results-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.results.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.results.arn
    container_name   = "results"
    container_port   = 8003
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-results-service-${var.environment}"
    Service = "results"
  }
}

# ECS Service - Worker
resource "aws_ecs_service" "worker" {
  name            = "${var.project_name}-worker-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  tags = {
    Name    = "${var.project_name}-worker-service-${var.environment}"
    Service = "worker"
  }
}

# ============================================================
# Phase 2+ Services: Portfolio, Risk, Regulatory, Ingestion
# ============================================================

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

# Target Group - Portfolio
resource "aws_lb_target_group" "portfolio" {
  name        = "${var.project_name}-port-tg-${var.environment}"
  port        = 8005
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-portfolio-tg-${var.environment}"
    Service = "portfolio"
  }
}

# Target Group - Risk
resource "aws_lb_target_group" "risk" {
  name        = "${var.project_name}-risk-tg-${var.environment}"
  port        = 8006
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-risk-tg-${var.environment}"
    Service = "risk"
  }
}

# Target Group - Regulatory
resource "aws_lb_target_group" "regulatory" {
  name        = "${var.project_name}-reg-tg-${var.environment}"
  port        = 8007
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-regulatory-tg-${var.environment}"
    Service = "regulatory"
  }
}

# Target Group - Ingestion
resource "aws_lb_target_group" "ingestion" {
  name        = "${var.project_name}-ing-tg-${var.environment}"
  port        = 8008
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name    = "${var.project_name}-ingestion-tg-${var.environment}"
    Service = "ingestion"
  }
}

# ALB Listener Rule - Portfolio
resource "aws_lb_listener_rule" "portfolio" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 400

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.portfolio.arn
  }

  condition {
    path_pattern {
      values = ["/portfolio/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-portfolio-${var.environment}"
    Service = "portfolio"
  }
}

# ALB Listener Rule - Risk
resource "aws_lb_listener_rule" "risk" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 500

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.risk.arn
  }

  condition {
    path_pattern {
      values = ["/risk/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-risk-${var.environment}"
    Service = "risk"
  }
}

# ALB Listener Rule - Regulatory
resource "aws_lb_listener_rule" "regulatory" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 600

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.regulatory.arn
  }

  condition {
    path_pattern {
      values = ["/regulatory/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-regulatory-${var.environment}"
    Service = "regulatory"
  }
}

# ALB Listener Rule - Ingestion
resource "aws_lb_listener_rule" "ingestion" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 700

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ingestion.arn
  }

  condition {
    path_pattern {
      values = ["/ingestion/*"]
    }
  }

  tags = {
    Name    = "${var.project_name}-alb-rule-ingestion-${var.environment}"
    Service = "ingestion"
  }
}

# ECS Service - Portfolio
resource "aws_ecs_service" "portfolio" {
  name            = "${var.project_name}-portfolio-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.portfolio.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.portfolio.arn
    container_name   = "portfolio"
    container_port   = 8005
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-portfolio-service-${var.environment}"
    Service = "portfolio"
  }
}

# ECS Service - Risk
resource "aws_ecs_service" "risk" {
  name            = "${var.project_name}-risk-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.risk.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.risk.arn
    container_name   = "risk"
    container_port   = 8006
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-risk-service-${var.environment}"
    Service = "risk"
  }
}

# ECS Service - Regulatory
resource "aws_ecs_service" "regulatory" {
  name            = "${var.project_name}-regulatory-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.regulatory.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.regulatory.arn
    container_name   = "regulatory"
    container_port   = 8007
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-regulatory-service-${var.environment}"
    Service = "regulatory"
  }
}

# ECS Service - Ingestion
resource "aws_ecs_service" "ingestion" {
  name            = "${var.project_name}-ingestion-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ingestion.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ingestion.arn
    container_name   = "ingestion"
    container_port   = 8008
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name    = "${var.project_name}-ingestion-service-${var.environment}"
    Service = "ingestion"
  }
}
