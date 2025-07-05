#!/bin/bash

# Employee Directory Cleanup Script
# This script removes all resources created for the application

set -e

# Configuration
CLUSTER_NAME="employee-directory"
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

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

# Confirm cleanup
confirm_cleanup() {
    log_warn "This will delete ALL resources for the Employee Directory application."
    log_warn "This action cannot be undone!"
    log_warn ""
    log_warn "Resources to be deleted:"
    log_warn "- EKS cluster and all workloads"
    log_warn "- RDS database (with all data)"
    log_warn "- VPC and networking components"
    log_warn "- ECR repositories and images"
    log_warn "- Secrets Manager secrets"
    log_warn "- IAM roles and policies"
    log_warn ""
    
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi
    
    log_warn "Starting cleanup in 10 seconds... Press Ctrl+C to cancel"
    sleep 10
}

# Delete Kubernetes resources
delete_k8s_resources() {
    log_step "Deleting Kubernetes resources..."
    
    # Configure kubectl if cluster exists
    if aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION &> /dev/null; then
        log_info "Configuring kubectl..."
        aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME 2>/dev/null || true
        
        # Delete application resources
        log_info "Deleting application resources..."
        kubectl delete -f k8s/network-policy.yaml --ignore-not-found=true
        kubectl delete -f k8s/hpa.yaml --ignore-not-found=true
        kubectl delete -f k8s/ingress.yaml --ignore-not-found=true
        kubectl delete -f k8s/frontend-deployment.yaml --ignore-not-found=true
        kubectl delete -f k8s/backend-deployment.yaml --ignore-not-found=true
        kubectl delete -f k8s/service-account.yaml --ignore-not-found=true
        kubectl delete -f k8s/secrets.yaml --ignore-not-found=true
        kubectl delete -f k8s/namespace.yaml --ignore-not-found=true
        
        # Delete monitoring if installed
        log_info "Deleting monitoring resources..."
        helm uninstall prometheus -n monitoring 2>/dev/null || true
        kubectl delete namespace monitoring --ignore-not-found=true
        
        # Delete ALB Controller
        log_info "Deleting ALB Controller..."
        helm uninstall aws-load-balancer-controller -n kube-system 2>/dev/null || true
        
        # Wait for resources to be deleted
        log_info "Waiting for resources to be deleted..."
        sleep 30
        
        log_info "Kubernetes resources deleted"
    else
        log_info "EKS cluster not found, skipping Kubernetes cleanup"
    fi
}

# Delete ECR repositories
delete_ecr_repositories() {
    log_step "Deleting ECR repositories..."
    
    local repositories=("employee-directory-frontend" "employee-directory-backend")
    
    for repo in "${repositories[@]}"; do
        if aws ecr describe-repositories --repository-names $repo --region $AWS_REGION &> /dev/null; then
            log_info "Deleting ECR repository: $repo"
            aws ecr delete-repository --repository-name $repo --region $AWS_REGION --force
        else
            log_info "ECR repository not found: $repo"
        fi
    done
    
    log_info "ECR repositories deleted"
}

# Destroy infrastructure
destroy_infrastructure() {
    log_step "Destroying infrastructure with Terraform..."
    
    cd terraform
    
    # Check if Terraform state exists
    if [ ! -f "terraform.tfstate" ] && [ ! -f ".terraform/terraform.tfstate" ]; then
        log_warn "No Terraform state found, skipping infrastructure destruction"
        cd ..
        return
    fi
    
    # Initialize Terraform (in case it's not initialized)
    log_info "Initializing Terraform..."
    terraform init
    
    # Destroy infrastructure
    log_info "Destroying infrastructure..."
    terraform destroy \
        -var="cluster_name=${CLUSTER_NAME}" \
        -var="aws_region=${AWS_REGION}" \
        -auto-approve
    
    cd ..
    
    log_info "Infrastructure destroyed"
}

# Clean up local files
cleanup_local_files() {
    log_step "Cleaning up local files..."
    
    # Ask about Terraform state files
    read -p "Do you want to remove Terraform state files? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing Terraform state files..."
        rm -rf terraform/.terraform
        rm -f terraform/terraform.tfstate*
        rm -f terraform/.terraform.lock.hcl
        rm -f terraform/tfplan
    fi
    
    # Remove backup files
    log_info "Removing backup files..."
    find . -name "*.bak" -delete 2>/dev/null || true
    
    # Remove temporary files
    rm -f alb-ingress-controller-policy.json 2>/dev/null || true
    
    log_info "Local cleanup completed"
}

# Verify cleanup
verify_cleanup() {
    log_step "Verifying cleanup..."
    
    local issues=0
    
    # Check EKS cluster
    if aws eks describe-cluster --name $CLUSTER_NAME --region $AWS_REGION &> /dev/null; then
        log_warn "EKS cluster still exists: $CLUSTER_NAME"
        ((issues++))
    fi
    
    # Check ECR repositories
    local repositories=("employee-directory-frontend" "employee-directory-backend")
    for repo in "${repositories[@]}"; do
        if aws ecr describe-repositories --repository-names $repo --region $AWS_REGION &> /dev/null; then
            log_warn "ECR repository still exists: $repo"
            ((issues++))
        fi
    done
    
    # Check RDS instances
    local rds_instances
    rds_instances=$(aws rds describe-db-instances --region $AWS_REGION --query "DBInstances[?contains(DBInstanceIdentifier, '${CLUSTER_NAME}')].DBInstanceIdentifier" --output text 2>/dev/null || echo "")
    if [ -n "$rds_instances" ]; then
        log_warn "RDS instances still exist: $rds_instances"
        ((issues++))
    fi
    
    # Check VPCs
    local vpcs
    vpcs=$(aws ec2 describe-vpcs --region $AWS_REGION --filters "Name=tag:Name,Values=${CLUSTER_NAME}-*" --query "Vpcs[].VpcId" --output text 2>/dev/null || echo "")
    if [ -n "$vpcs" ]; then
        log_warn "VPCs still exist: $vpcs"
        ((issues++))
    fi
    
    if [ $issues -eq 0 ]; then
        log_info "Cleanup verification passed - no resources found"
    else
        log_warn "Cleanup verification found $issues potential issues"
        log_warn "Some resources may take additional time to be fully deleted"
        log_warn "You may need to manually check and delete any remaining resources"
    fi
}

# Force cleanup for stuck resources
force_cleanup() {
    log_step "Performing force cleanup for stuck resources..."
    
    # Force delete Load Balancers
    log_info "Checking for stuck Load Balancers..."
    local lbs
    lbs=$(aws elbv2 describe-load-balancers --region $AWS_REGION --query "LoadBalancers[?contains(LoadBalancerName, '${CLUSTER_NAME}') || contains(to_string(Tags), '${CLUSTER_NAME}')].LoadBalancerArn" --output text 2>/dev/null || echo "")
    for lb in $lbs; do
        if [ -n "$lb" ]; then
            log_info "Force deleting Load Balancer: $lb"
            aws elbv2 delete-load-balancer --load-balancer-arn "$lb" --region $AWS_REGION 2>/dev/null || true
        fi
    done
    
    # Force delete Security Groups
    log_info "Checking for stuck Security Groups..."
    local sgs
    sgs=$(aws ec2 describe-security-groups --region $AWS_REGION --filters "Name=tag:Name,Values=${CLUSTER_NAME}-*" --query "SecurityGroups[].GroupId" --output text 2>/dev/null || echo "")
    for sg in $sgs; do
        if [ -n "$sg" ] && [ "$sg" != "default" ]; then
            log_info "Force deleting Security Group: $sg"
            aws ec2 delete-security-group --group-id "$sg" --region $AWS_REGION 2>/dev/null || true
        fi
    done
    
    # Force delete NAT Gateways
    log_info "Checking for stuck NAT Gateways..."
    local nats
    nats=$(aws ec2 describe-nat-gateways --region $AWS_REGION --filter "Name=tag:Name,Values=${CLUSTER_NAME}-*" --query "NatGateways[?State=='available'].NatGatewayId" --output text 2>/dev/null || echo "")
    for nat in $nats; do
        if [ -n "$nat" ]; then
            log_info "Force deleting NAT Gateway: $nat"
            aws ec2 delete-nat-gateway --nat-gateway-id "$nat" --region $AWS_REGION 2>/dev/null || true
        fi
    done
    
    log_info "Force cleanup completed"
}

# Main cleanup function
main() {
    log_info "Starting Employee Directory cleanup..."
    log_info "Cluster: $CLUSTER_NAME"
    log_info "Region: $AWS_REGION"
    log_info "Account: $AWS_ACCOUNT_ID"
    
    confirm_cleanup
    delete_k8s_resources
    delete_ecr_repositories
    destroy_infrastructure
    cleanup_local_files
    verify_cleanup
    
    # Ask if user wants to perform force cleanup
    read -p "Do you want to perform force cleanup for any stuck resources? (y/n): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        force_cleanup
        verify_cleanup
    fi
    
    log_info "Cleanup completed!"
    log_info ""
    log_info "Summary:"
    log_info "- Kubernetes resources deleted"
    log_info "- ECR repositories deleted"
    log_info "- Infrastructure destroyed"
    log_info "- Local files cleaned up"
    log_info ""
    log_warn "Note: Some AWS resources may take additional time to be fully deleted."
    log_warn "Check the AWS console to verify all resources have been removed."
    log_info ""
    log_info "If you encounter any issues, you can:"
    log_info "1. Check the AWS console for remaining resources"
    log_info "2. Run this script again with force cleanup"
    log_info "3. Manually delete any remaining resources"
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
        --force)
            FORCE_CLEANUP=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cluster-name NAME    EKS cluster name (default: employee-directory)"
            echo "  --region REGION        AWS region (default: us-west-2)"
            echo "  --force                Skip confirmation prompts"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Skip confirmation if force flag is set
if [ "${FORCE_CLEANUP:-false}" = "true" ]; then
    log_warn "Force cleanup enabled - skipping confirmation"
else
    # Run main function
    main "$@"
fi