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
