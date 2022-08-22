resource "aws_db_instance" "rds" {
  identifier                = "mysql"
  allocated_storage         = 5
  max_allocated_storage     = 10
  engine                    = "mysql"
  engine_version            = "5.7"
  instance_class            = "db.t3.micro"
  db_name                   = var.database_name
  username                  = var.database_user
  password                  = var.database_password
  db_subnet_group_name      = aws_db_subnet_group.rds.id
  vpc_security_group_ids    = [aws_security_group.rds.id]
  skip_final_snapshot       = true
  final_snapshot_identifier = "Ignore"
}

output "rds_address" {
  description = "RDS address"
  value       = aws_db_instance.rds.endpoint
}

output "rds_port" {
  description = "RDS port"
  value       = aws_db_instance.rds.port
}

output "rds_user" {
  description = "RDS user"
  value = aws_db_instance.rds.username
}

