resource "aws_ecs_cluster" "cluster" {
  name = "cluster"
}

resource "aws_ecs_service" "api" {
  name                 = "api-service"
  cluster              = aws_ecs_cluster.cluster.id
  task_definition      = aws_ecs_task_definition.api.arn
  launch_type          = "FARGATE"
  scheduling_strategy  = "REPLICA"
  desired_count        = 1
  force_new_deployment = true

  network_configuration {
    subnets = aws_subnet.private.*.id
    assign_public_ip = false
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.alb-target_group.arn
    container_name   = "api-task"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.listener, aws_db_instance.rds]
}