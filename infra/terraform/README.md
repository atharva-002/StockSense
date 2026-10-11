# StockSense AWS infrastructure (Terraform)

Minimal, production-flavoured Terraform for StockSense:

- **S3** bucket for versioned model artefacts (encrypted).
- **ECR** repository to push the API Docker image.
- **ECS Fargate** cluster + task + service that runs the API.
- **IAM** execution + task roles (least privilege: task role can read artefacts bucket).
- **CloudWatch** log group with 14-day retention.

## Usage

```bash
cd infra/terraform
terraform init
terraform validate     # syntax check only
terraform plan \
  -var "artifact_bucket_name=my-stocksense-artifacts-<unique>" \
  -var 'subnet_ids=["subnet-aaa","subnet-bbb"]' \
  -var 'security_group_ids=["sg-123"]'
# terraform apply ... (requires real AWS credentials)
```

> **Note** The free deployment path (Render + Vercel) does not require this
> module. It is here to demonstrate production-flavoured infra.

## Push an image

```bash
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
docker build -t stocksense-api:latest -f ../../Dockerfile ../..
docker tag stocksense-api:latest $ECR_URL:latest
docker push $ECR_URL:latest
aws ecs update-service --cluster stocksense-api-cluster --service stocksense-api --force-new-deployment
```
