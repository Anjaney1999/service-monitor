resource "aws_cloudwatch_event_rule" "event_rule" {
  name = "schedule-event"
  schedule_expression = var.execution_rate
  depends_on = [aws_db_instance.rds]
}

resource "aws_cloudwatch_event_target" "scheduled_task" {
  rule = aws_cloudwatch_event_rule.event_rule.name
  target_id = "compute-container" 
  arn = aws_ecs_cluster.cluster.arn
  role_arn = aws_iam_role.scheduler.arn
  ecs_target {
    launch_type = "FARGATE"
    platform_version = "LATEST"
    task_count = 1
    task_definition_arn = aws_ecs_task_definition.compute.arn
    network_configuration {
      subnets = aws_subnet.private.*.id
    }
  }
}