resource "aws_iam_role" "ecs" {
  name = "ecs_role"
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": ["ecs.amazonaws.com", "ecs-tasks.amazonaws.com"]
        },
        "Effect": "Allow"
      }
    ]
  })
}

resource "aws_iam_policy" "ecs" {
  name   = "ecs_policy"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
            "ecs:*",
            "ec2:*",
            "elasticloadbalancing:*",
            "ecr:*",
            "cloudwatch:*",
            "rds:*",
            "logs:*"
        ],
        "Resource": "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_attach" {
  role       = aws_iam_role.ecs.name
  policy_arn = aws_iam_policy.ecs.arn
}

resource "aws_iam_role" "scheduler" {
  name = "scheduler-role"
  assume_role_policy =  jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "",
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "scheduler" {
  name = "scheduler-policy"
  policy = jsonencode({
      "Version": "2012-10-17",
      "Statement": [
        {
            "Effect": "Allow",
            "Action": "ecs:RunTask",
            "Resource": "${aws_ecs_task_definition.compute.arn}"
        }
      ]
  })
}

resource "aws_iam_role_policy_attachment" "scheduler_attach" {
  role       = aws_iam_role.scheduler.name
  policy_arn = aws_iam_policy.scheduler.arn
}