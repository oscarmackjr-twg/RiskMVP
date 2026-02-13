# AWS Cloud Map — Private DNS namespace for inter-service discovery
# Backend ECS services register here so nginx can resolve them by name

resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "iprs.local"
  description = "Private DNS namespace for IPRS backend services"
  vpc         = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-dns-namespace-${var.environment}"
  }
}

# Service Discovery registrations — one per backend service

resource "aws_service_discovery_service" "marketdata" {
  name = "marketdata"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-marketdata-${var.environment}"
    Service = "marketdata"
  }
}

resource "aws_service_discovery_service" "orchestrator" {
  name = "orchestrator"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-orchestrator-${var.environment}"
    Service = "orchestrator"
  }
}

resource "aws_service_discovery_service" "results" {
  name = "results"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-results-${var.environment}"
    Service = "results"
  }
}

resource "aws_service_discovery_service" "worker" {
  name = "worker"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-worker-${var.environment}"
    Service = "worker"
  }
}

resource "aws_service_discovery_service" "portfolio" {
  name = "portfolio"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-portfolio-${var.environment}"
    Service = "portfolio"
  }
}

resource "aws_service_discovery_service" "risk" {
  name = "risk"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-risk-${var.environment}"
    Service = "risk"
  }
}

resource "aws_service_discovery_service" "regulatory" {
  name = "regulatory"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-regulatory-${var.environment}"
    Service = "regulatory"
  }
}

resource "aws_service_discovery_service" "ingestion" {
  name = "ingestion"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = {
    Name    = "${var.project_name}-sd-ingestion-${var.environment}"
    Service = "ingestion"
  }
}
