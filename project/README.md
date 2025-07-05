# Multi-tier Support Portal on EKS with EC2 + Fargate Hybrid Deployment

A comprehensive employee directory system deployed as microservices on Amazon EKS, featuring a React frontend on Fargate and a Flask backend on EC2 nodes, with PostgreSQL on Amazon RDS.

## Architecture Overview

```
┌────────────┐ ┌──────────────────────────┐
│ Internet   │──────▶│ ALB Ingress Controller │
└────────────┘ └────────┬─────────────────┘
                        │
               ┌────────▼────────┐
               │ Frontend (Fargate) │
               │ Namespace: frontend │
               └────────┬────────┘
                        │
        ┌──────────────────────────▼────────────────────────┐
        │ Backend Service (EC2 nodes - backend ns) │
        └──────────────────────────┬────────────────────────┘
                                   │
                          ┌──────────▼──────────┐
                          │ RDS (PostgreSQL)    │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ AWS Secrets Manager │
                          └─────────────────────┘
```

## Features

### Frontend (React on Fargate)
- Modern, responsive employee directory interface
- Employee search and filtering capabilities
- CRUD operations for employee management
- Real-time updates and notifications
- Mobile-optimized design

### Backend (Flask on EC2)
- RESTful API with comprehensive endpoints
- JWT authentication and authorization
- Database connection pooling
- Health check endpoints
- Comprehensive logging and monitoring

### Infrastructure
- **EKS Cluster**: Kubernetes orchestration
- **Fargate**: Serverless containers for frontend
- **EC2 Node Groups**: Dedicated compute for backend
- **RDS PostgreSQL**: Managed database service
- **Secrets Manager**: Secure credential storage
- **ALB**: Application Load Balancer with SSL termination
- **VPC**: Secure network isolation

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- kubectl installed
- Docker installed
- Terraform installed
- Helm installed

### Deployment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd employee-directory
   ```

2. **Deploy infrastructure and application**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

3. **Access the application**
   The deployment script will output the ALB URL where the application is accessible.

### Manual Deployment Steps

If you prefer to deploy manually:

1. **Deploy Infrastructure**
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

2. **Configure kubectl**
   ```bash
   aws eks update-kubeconfig --region us-west-2 --name employee-directory
   ```

3. **Build and Push Images**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com
   
   # Build and push frontend
   cd frontend
   docker build -t employee-directory-frontend .
   docker tag employee-directory-frontend:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/employee-directory-frontend:latest
   docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/employee-directory-frontend:latest
   
   # Build and push backend
   cd ../backend
   docker build -t employee-directory-backend .
   docker tag employee-directory-backend:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/employee-directory-backend:latest
   docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/employee-directory-backend:latest
   ```

4. **Deploy Kubernetes Resources**
   ```bash
   kubectl apply -f k8s/
   ```

## Configuration

### Environment Variables

#### Backend
- `DATABASE_URL`: Database connection string (from Secrets Manager)
- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `AWS_REGION`: AWS region for Secrets Manager
- `DB_SECRET_NAME`: Secrets Manager secret name

#### Frontend
- `REACT_APP_API_URL`: Backend API URL

### AWS Resources

#### Required IAM Permissions
- EKS cluster management
- EC2 instance management
- RDS database management
- Secrets Manager access
- ECR repository access
- ALB management

#### Secrets Manager
The application uses AWS Secrets Manager to store:
- Database credentials
- JWT secret keys
- Other sensitive configuration

## Monitoring and Observability

### Health Checks
- Backend: `/health` endpoint
- Frontend: Root path health check
- Database: Connection monitoring

### Metrics and Alerting
- Prometheus metrics collection
- Grafana dashboards
- CloudWatch integration
- Custom alerts for:
  - High CPU/memory usage
  - Pod restart rates
  - Database connection counts
  - Application availability

### Logging
- Centralized logging with CloudWatch
- Application logs from all components
- EKS control plane logs
- Database query logs

## Security

### Network Security
- VPC with private subnets
- Security groups with minimal required access
- Network policies for pod-to-pod communication
- ALB with SSL termination

### Application Security
- JWT-based authentication
- RBAC for Kubernetes resources
- IRSA (IAM Roles for Service Accounts)
- Secrets stored in AWS Secrets Manager
- Container security scanning

### Database Security
- RDS in private subnets
- Encryption at rest and in transit
- Regular automated backups
- Parameter group hardening

## Scaling

### Horizontal Pod Autoscaling (HPA)
- CPU and memory-based scaling
- Custom metrics support
- Separate scaling policies for frontend and backend

### Cluster Autoscaling
- EC2 node group autoscaling
- Fargate automatic scaling
- Cost-optimized instance selection

## Disaster Recovery

### Backup Strategy
- RDS automated backups (7-day retention)
- Point-in-time recovery
- Cross-region backup replication (optional)

### High Availability
- Multi-AZ deployment
- Load balancer health checks
- Automatic failover capabilities

## Development

### Local Development

#### Frontend
```bash
cd frontend
npm install
npm start
```

#### Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Testing
```bash
# Frontend tests
cd frontend
npm test

# Backend tests
cd backend
python -m pytest
```

## Cleanup

To remove all resources:

```bash
chmod +x scripts/cleanup.sh
./scripts/cleanup.sh
```

## Troubleshooting

### Common Issues

1. **Pod scheduling issues**
   - Check node selectors and taints
   - Verify resource requests and limits
   - Check Fargate profile configuration

2. **Database connection issues**
   - Verify Secrets Manager access
   - Check security group rules
   - Validate RDS endpoint connectivity

3. **ALB not accessible**
   - Check ingress configuration
   - Verify ALB controller installation
   - Check security group rules

### Useful Commands

```bash
# Check pod status
kubectl get pods -A

# View pod logs
kubectl logs -f deployment/backend-deployment -n backend

# Check ingress status
kubectl get ingress -n frontend

# Describe problematic resources
kubectl describe pod <pod-name> -n <namespace>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review AWS EKS documentation
- Consult Kubernetes documentation