data "aws_region" "current" {}

resource "aws_ecs_task_definition" "api" {
  family = "api-task" 
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs.arn
  task_role_arn            = aws_iam_role.ecs.arn

  container_definitions = <<DEFINITION
  [
    {
      "name": "api-task",
      "image": "${var.api_repo}:latest",
      "entryPoint": [],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-create-group": "True",
          "awslogs-group": "/ecs/api",
          "awslogs-region": "${data.aws_region.current.name}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {"name": "DB_ADDRESS", "value": "${aws_db_instance.rds.endpoint}"},
        {"name": "DB_PORT", "value": "${aws_db_instance.rds.port}"},
        {"name": "DB_NAME", "value": "${var.database_name}"},
        {"name": "DB_USER", "value": "${var.database_user}"},
        {"name": "DB_PASSWORD", "value": "${var.database_password}"},
        {"name": "MIN_POOL", "value": "${var.min_pool}"},
        {"name": "MAX_POOL", "value": "${var.max_pool}"},
        {"name": "TIMEOUT", "value": "${var.timeout}"},
        {"name": "CACHE_ADDRESS", "value": "${element(aws_elasticache_cluster.cache.cache_nodes, 0).address}"},
        {"name": "CACHE_PORT", "value": "${element(aws_elasticache_cluster.cache.cache_nodes, 0).port}"}
      ], 
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000
        }
      ],
      "cpu": 128,
      "memory": 512,
      "networkMode": "awsvpc"
    }
  ]
  DEFINITION
}

resource "aws_ecs_task_definition" "compute" {
  family = "compute-task" 
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs.arn
  task_role_arn            = aws_iam_role.ecs.arn
  depends_on = [aws_db_instance.rds, aws_elasticache_cluster.cache]

  container_definitions = <<DEFINITION
  [
    {
      "name": "compute-task",
      "image": "${var.compute_repo}:latest",
      "entryPoint": [],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-create-group": "True",
          "awslogs-group": "/ecs/compute",
          "awslogs-region": "${data.aws_region.current.name}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {"name": "DB_ADDRESS", "value": "${aws_db_instance.rds.endpoint}"},
        {"name": "DB_PORT", "value": "${aws_db_instance.rds.port}"},
        {"name": "DB_NAME", "value": "${var.database_name}"},
        {"name": "DB_USER", "value": "${var.database_user}"},
        {"name": "DB_PASSWORD", "value": "${var.database_password}"},
        {"name": "MIN_POOL", "value": "${var.min_pool}"},
        {"name": "MAX_POOL", "value": "${var.max_pool}"},
        {"name": "TIMEOUT", "value": "${var.timeout}"},
        {"name": "CACHE_ADDRESS", "value": "${element(aws_elasticache_cluster.cache.cache_nodes, 0).address}"},
        {"name": "CACHE_PORT", "value": "${element(aws_elasticache_cluster.cache.cache_nodes, 0).port}"}
      ], 
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000
        }
      ],
      "cpu": 512,
      "memory": 1024,
      "networkMode": "awsvpc"
    }
  ]
  DEFINITION
}