output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "s3_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "ecs_cluster" {
  value = aws_ecs_cluster.this.name
}

output "ecs_service" {
  value = aws_ecs_service.api.name
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.api.name
}
