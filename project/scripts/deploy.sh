#!/bin/bash

# Employee Directory Deployment Script
# This script deploys the multi-tier application to EKS

set -e

# Configuration
CLUSTER_NAME="employee-directory"
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    # Check if required tools are installed
    local tools=("aws" "kubectl" "docker" "terraform" "helm")
    for tool in "${tools[@]}"; do
        if ! command -v $tool &> /dev/null; then
            log_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_step "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Validate configuration
    log_info "Validating Terraform configuration..."
    terraform validate
    
    # Plan deployment
    log_info "Planning infrastructure deployment..."
    terraform plan \
        -var="cluster_name=${CLUSTER_NAME}" \
        -var="aws_region=${AWS_REGION}" \
        -out=tfplan
    
    # Apply deployment
    log_info "Applying infrastructure deployment..."
    terraform apply tfplan
    
    cd ..
    
    log_info "Infrastructure deployment completed"
}

# Configure kubectl
configure_kubectl() {
    log_step "Configuring kubectl..."
    
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    
    # Verify connection
    log_info "Verifying cluster connection..."
    kubectl cluster-info
    
    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    kubectl wait --for=condition=Ready nodes --all --timeout=300s
    
    log_info "kubectl configured successfully"
}

# Create ECR repositories
create_ecr_repositories() {
    log_step "Creating ECR repositories..."
    
    local repositories=("employee-directory-frontend" "employee-directory-backend")
    
    for repo in "${repositories[@]}"; do
        if ! aws ecr describe-repositories --repository-names $repo --region $AWS_REGION &> /dev/null; then
            log_info "Creating ECR repository: $repo"
            aws ecr create-repository --repository-name $repo --region $AWS_REGION
        else
            log_info "ECR repository already exists: $repo"
        fi
    done
}

# Build and push Docker images
build_and_push_images() {
    log_step "Building and pushing Docker images..."
    
    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Build and push frontend
    log_info "Building frontend image..."
    cd frontend
    docker build -t employee-directory-frontend .
    docker tag employee-directory-frontend:latest $ECR_REGISTRY/employee-directory-frontend:latest
    docker tag employee-directory-frontend:latest $ECR_REGISTRY/employee-directory-frontend:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    log_info "Pushing frontend image..."
    docker push $ECR_REGISTRY/employee-directory-frontend:latest
    docker push $ECR_REGISTRY/employee-directory-frontend:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    cd ..
    
    # Build and push backend
    log_info "Building backend image..."
    cd backend
    docker build -t employee-directory-backend .
    docker tag employee-directory-backend:latest $ECR_REGISTRY/employee-directory-backend:latest
    docker tag employee-directory-backend:latest $ECR_REGISTRY/employee-directory-backend:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    
    log_info "Pushing backend image..."
    docker push $ECR_REGISTRY/employee-directory-backend:latest
    docker push $ECR_REGISTRY/employee-directory-backend:$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    cd ..
    
    log_info "Docker images built and pushed successfully"
}

# Install ALB Ingress Controller
install_alb_controller() {
    log_step "Installing ALB Ingress Controller..."
    
    # Check if already installed
    if helm list -n kube-system | grep -q aws-load-balancer-controller; then
        log_info "ALB Ingress Controller already installed"
        return
    fi
    
    # Get ALB controller role ARN from Terraform output
    local alb_role_arn
    alb_role_arn=$(terraform -chdir=terraform output -raw alb_ingress_controller_role_arn)
    
    # Create service account
    log_info "Creating ALB controller service account..."
    kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  labels:
    app.kubernetes.io/component: controller
    app.kubernetes.io/name: aws-load-balancer-controller
  name: aws-load-balancer-controller
  namespace: kube-system
  annotations:
    eks.amazonaws.com/role-arn: ${alb_role_arn}
EOF
    
    # Add EKS Helm repository
    log_info "Adding EKS Helm repository..."
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update
    
    # Install ALB Controller
    log_info "Installing ALB Ingress Controller..."
    helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=$CLUSTER_NAME \
        --set serviceAccount.create=false \
        --set serviceAccount.name=aws-load-balancer-controller \
        --set region=$AWS_REGION \
        --set vpcId=$(terraform -chdir=terraform output -raw vpc_id)
    
    # Wait for deployment
    log_info "Waiting for ALB controller to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/aws-load-balancer-controller -n kube-system
    
    log_info "ALB Ingress Controller installed successfully"
}

# Deploy Kubernetes manifests
deploy_k8s_manifests() {
    log_step "Deploying Kubernetes manifests..."
    
    # Create temporary directory for processed manifests
    local temp_dir=$(mktemp -d)
    cp -r k8s/* $temp_dir/
    
    # Update image references in deployment files
    log_info "Updating image references..."
    sed -i.bak "s|your-account.dkr.ecr.us-east-1.amazonaws.com|$ECR_REGISTRY|g" $temp_dir/backend-deployment.yaml
    sed -i.bak "s|your-account.dkr.ecr.us-east-1.amazonaws.com|$ECR_REGISTRY|g" $temp_dir/frontend-deployment.yaml
    
    # Update IRSA role ARNs
    log_info "Updating IRSA role ARNs..."
    local backend_role_arn
    backend_role_arn=$(terraform -chdir=terraform output -raw backend_irsa_role_arn)
    sed -i.bak "s|arn:aws:iam::ACCOUNT_ID:role/employee-directory-backend-role|$backend_role_arn|g" $temp_dir/service-account.yaml
    
    # Update secrets with actual ARNs
    log_info "Updating secret references..."
    local db_secret_arn
    local jwt_secret_arn
    db_secret_arn=$(terraform -chdir=terraform output -raw secrets_manager_db_secret_arn)
    jwt_secret_arn=$(terraform -chdir=terraform output -raw secrets_manager_jwt_secret_arn)
    
    # Update backend deployment with secret names
    sed -i.bak "s|employee-directory-db-credentials|$(basename $db_secret_arn)|g" $temp_dir/backend-deployment.yaml
    sed -i.bak "s|employee-directory-jwt-secret|$(basename $jwt_secret_arn)|g" $temp_dir/backend-deployment.yaml
    
    # Apply manifests in order
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f $temp_dir/namespace.yaml
    kubectl apply -f $temp_dir/secrets.yaml
    kubectl apply -f $temp_dir/service-account.yaml
    kubectl apply -f $temp_dir/backend-deployment.yaml
    kubectl apply -f $temp_dir/frontend-deployment.yaml
    kubectl apply -f $temp_dir/ingress.yaml
    kubectl apply -f $temp_dir/hpa.yaml
    kubectl apply -f $temp_dir/network-policy.yaml
    
    # Clean up temporary directory
    rm -rf $temp_dir
    
    log_info "Kubernetes manifests deployed successfully"
}

# Wait for deployments to be ready
wait_for_deployments() {
    log_step "Waiting for deployments to be ready..."
    
    log_info "Waiting for backend deployment..."
    kubectl wait --for=condition=available --timeout=600s deployment/backend-deployment -n backend
    
    log_info "Waiting for frontend deployment..."
    kubectl wait --for=condition=available --timeout=600s deployment/frontend-deployment -n frontend
    
    # Check pod status
    log_info "Checking pod status..."
    kubectl get pods -n backend
    kubectl get pods -n frontend
    
    log_info "All deployments are ready"
}

# Get application URL
get_application_url() {
    log_step "Getting application URL..."
    
    # Wait for ALB to be provisioned
    log_info "Waiting for ALB to be provisioned..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local alb_url
        alb_url=$(kubectl get ingress employee-directory-ingress -n frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
        
        if [ -n "$alb_url" ]; then
            log_info "Application is available at: http://$alb_url"
            log_info "Note: It may take a few more minutes for the ALB to be fully ready"
            return
        fi
        
        log_info "Waiting for ALB... (attempt $attempt/$max_attempts)"
        sleep 30
        ((attempt++))
    done
    
    log_warn "ALB URL not yet available. Check ingress status with: kubectl get ingress -n frontend"
}

# Setup monitoring (optional)
setup_monitoring() {
    log_step "Setting up monitoring (optional)..."
    
    if [ "${SETUP_MONITORING:-false}" = "true" ]; then
        log_info "Installing Prometheus and Grafana..."
        
        # Add Prometheus Helm repository
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        helm repo update
        
        # Install Prometheus
        helm install prometheus prometheus-community/kube-prometheus-stack \
            --namespace monitoring \
            --create-namespace \
            --set grafana.adminPassword=admin123
        
        log_info "Monitoring stack installed. Access Grafana at: kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
    else
        log_info "Skipping monitoring setup. Set SETUP_MONITORING=true to enable."
    fi
}

# Cleanup function for error handling
cleanup_on_error() {
    log_error "Deployment failed. Cleaning up..."
    
    # Remove any partially created resources
    kubectl delete -f k8s/ --ignore-not-found=true 2>/dev/null || true
    
    # Note: We don't automatically destroy Terraform resources to avoid data loss
    log_warn "Terraform resources were not automatically destroyed."
    log_warn "Run 'terraform destroy' manually if you want to remove all infrastructure."
}

# Main deployment function
main() {
    log_info "Starting Employee Directory deployment..."
    log_info "Cluster: $CLUSTER_NAME"
    log_info "Region: $AWS_REGION"
    log_info "Account: $AWS_ACCOUNT_ID"
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    # Run deployment steps
    check_prerequisites
    deploy_infrastructure
    configure_kubectl
    create_ecr_repositories
    build_and_push_images
    install_alb_controller
    deploy_k8s_manifests
    wait_for_deployments
    get_application_url
    setup_monitoring
    
    log_info "Deployment completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Configure DNS to point to the ALB (if using custom domain)"
    log_info "2. Set up SSL certificate in ACM and update ingress"
    log_info "3. Configure monitoring and alerting"
    log_info "4. Set up backup and disaster recovery procedures"
    log_info ""
    log_info "Useful commands:"
    log_info "- View pods: kubectl get pods -A"
    log_info "- View services: kubectl get svc -A"
    log_info "- View ingress: kubectl get ingress -n frontend"
    log_info "- View logs: kubectl logs -f deployment/backend-deployment -n backend"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cluster-name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        --region)
            AWS_REGION="$2"
            shift 2
            ;;
        --monitoring)
            SETUP_MONITORING=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cluster-name NAME    EKS cluster name (default: employee-directory)"
            echo "  --region REGION        AWS region (default: us-east-1)"
            echo "  --monitoring           Install monitoring stack"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"