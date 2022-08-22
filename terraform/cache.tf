resource "aws_elasticache_cluster" "cache" {
  cluster_id           = "cluster"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis3.2"
  subnet_group_name    = aws_elasticache_subnet_group.cache.name
  security_group_ids   = [aws_security_group.cache.id]
  engine_version       = "3.2.10"
  port                 = 6379
}

output "cache_host" {
  value = aws_elasticache_cluster.cache.cache_nodes
}

output "cache_port" {
  value = aws_elasticache_cluster.cache.port
}