data "aws_availability_zones" "available_zones" {
  state = "available"
}

resource "aws_vpc" "vpc" {
  cidr_block           = var.cidr
  enable_dns_hostnames = true
}

resource "aws_internet_gateway" "vpc" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.vpc.id
  count             = 2
  cidr_block        = cidrsubnet(aws_vpc.vpc.cidr_block, 8, count.index)
  availability_zone = element(data.aws_availability_zones.available_zones.names, count.index)
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.vpc.id
  cidr_block              = cidrsubnet(aws_vpc.vpc.cidr_block, 8, 2 + count.index)
  availability_zone       = element(data.aws_availability_zones.available_zones.names, count.index)
  map_public_ip_on_launch = true
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc.id
}

resource "aws_route" "public" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.vpc.id
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = element(aws_subnet.public.*.id, count.index)
  route_table_id = aws_route_table.public.id
}

resource "aws_db_subnet_group" "rds" {
  name        = "rds-subnet-group"
  description = "Subnet group"
  subnet_ids  = aws_subnet.private.*.id
}

resource "aws_elasticache_subnet_group" "cache" {
  name        = "cache-subnet-group"
  description = "Subnet group"
  subnet_ids  = aws_subnet.private.*.id
}