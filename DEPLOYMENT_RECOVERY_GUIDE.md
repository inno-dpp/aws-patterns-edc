# AWS Patterns EDC - Deployment Recovery Guide

This guide explains how to deploy the AWS Patterns EDC data space when starting from a fresh repository clone, or when recovering from missing Terraform state files.

## Overview

The AWS Patterns EDC uses a **two-tier Terraform deployment** with cross-references between layers. When state files are missing or infrastructure exists without corresponding state, special recovery procedures are needed.

## Prerequisites

Before starting, ensure you have:

- AWS CLI configured with appropriate permissions
- Terraform ~> 1.12.2 installed
- kubectl 1.32+ installed
- Python 3.8+ (for DID generation)
- Domain name with ACM certificate
- Route 53 hosted zone configured

## Deployment Scenarios

### Scenario 1: Fresh Repository Clone (No Infrastructure)

This is the standard deployment from scratch.

#### Step 1: Deploy EKS Infrastructure

```bash
cd infrastructure/eks

# Initialize Terraform
terraform init

# Apply with your domain name
terraform apply -var="domain_name=<YOUR_DOMAIN_NAME>"

# Configure kubectl
aws eks update-kubeconfig --name aws-patterns-edc --region <AWS_REGION>

# Verify cluster
kubectl get nodes
```

#### Step 2: Generate DID Resources

```bash
cd ../../deployment/assets/did

# Install Python dependencies
python3 -m pip install -r requirements.txt

# Generate DID credentials
python3 jwt-gen.py --regenerate-keys --sign-jwts --domain <YOUR_DOMAIN_NAME> --assets-dir .
```

#### Step 3: Deploy Data Space Components

```bash
cd ../..  # Back to deployment directory

# Initialize Terraform
terraform init

# Apply deployment
terraform apply
```

#### Step 4: Verify Deployment

```bash
# Check all pods are running
kubectl get pods --all-namespaces | grep -E "(authority|companyx|companyy)"

# Test endpoints
curl -k https://issuer.<YOUR_DOMAIN>/health
curl -k https://companyx.<YOUR_DOMAIN>/api/v1/management/health
```

---

### Scenario 2: Infrastructure Exists, State Files Missing

This happens when infrastructure was previously deployed but Terraform state files are lost or corrupted.

#### Step 1: Verify Infrastructure Exists

```bash
# Check if EKS cluster exists
aws eks list-clusters --region <AWS_REGION>

# Check if kubectl is configured
kubectl get nodes

# Identify your domain from existing Route53 zones
aws route53 list-hosted-zones --query 'HostedZones[].Name' --output text
```

#### Step 2: Restore EKS Infrastructure State

```bash
cd infrastructure/eks

# Initialize Terraform
terraform init

# Run plan to see what Terraform thinks needs creation
terraform plan -var="domain_name=<DISCOVERED_DOMAIN_NAME>"

# Apply to restore state (Terraform will detect existing resources)
terraform apply -var="domain_name=<DISCOVERED_DOMAIN_NAME>" -auto-approve
```

**Important**: This is safe because Terraform will detect existing resources and update the state file rather than recreating them.

#### Step 3: Handle Data Space Layer

If data space components already exist:

```bash
cd ../../deployment

# Check if DID credentials exist
ls -la assets/did/*.jwt

# If missing, regenerate DID credentials
cd assets/did
python3 jwt-gen.py --regenerate-keys --sign-jwts --domain <DOMAIN_NAME> --assets-dir .
cd ../..

# Test if plan works
terraform plan
```

If namespaces already exist, you'll see errors like:
```
Error: namespaces "authority" already exists
```

#### Step 4: Import Existing Resources (If Needed)

```bash
# Import existing namespaces
terraform import kubernetes_namespace.authority_namespace authority
terraform import kubernetes_namespace.companyx_namespace companyx
terraform import kubernetes_namespace.companyy_namespace companyy

# Import other existing resources as needed
# (This may require identifying resource names in the cluster)

# After importing, run apply
terraform apply
```

---

### Scenario 3: Adding New Organizations

When adding new organizations to existing infrastructure:

#### Step 1: Add Organization Configuration

Use the automation script:

```bash
cd scripts

# Install dependencies
python3 -m pip install -r requirements.txt

# Add new organization
python3 add-organization.py --org-name companyz --domain <YOUR_DOMAIN_NAME>
```

#### Step 2: Update DID Credentials

```bash
cd ../deployment/assets/did

# Regenerate credentials including new organization
python3 jwt-gen.py --regenerate-keys --sign-jwts --domain <YOUR_DOMAIN_NAME> --assets-dir .
```

#### Step 3: Apply Changes

```bash
cd ../..  # Back to deployment directory

# Plan and apply
terraform plan
terraform apply
```

## Common Issues and Solutions

### Issue 1: Remote State Not Found

**Error**: `Error: Unable to find remote state`

**Cause**: EKS infrastructure state file missing

**Solution**: Follow Scenario 2 - restore EKS infrastructure state first

### Issue 2: DID Credential Files Missing

**Error**: `no file exists at "./assets/did/companyx.membership.jwt"`

**Cause**: DID credentials not generated

**Solution**: Run the DID generation script:
```bash
cd deployment/assets/did
python3 jwt-gen.py --regenerate-keys --sign-jwts --domain <DOMAIN_NAME> --assets-dir .
```

### Issue 3: Namespace Already Exists

**Error**: `namespaces "authority" already exists`

**Cause**: Resources exist but not in Terraform state

**Solution**: Import existing resources:
```bash
terraform import kubernetes_namespace.authority_namespace authority
```

### Issue 4: Domain Name Not Set

**Error**: `No value for required variable "domain_name"`

**Cause**: Domain not provided in terraform command

**Solution**: Always specify domain:
```bash
terraform apply -var="domain_name=your-domain.com"
```

## State File Locations

Understanding where Terraform stores state:

```
infrastructure/eks/terraform.tfstate          # EKS infrastructure state
deployment/terraform.tfstate                  # Data space components state
```

The deployment layer references the EKS state via:
```hcl
data "terraform_remote_state" "eks" {
  backend = "local"
  config = {
    path = "../infrastructure/eks/terraform.tfstate"
  }
}
```

## Recovery Verification Commands

After any recovery procedure, verify the deployment:

```bash
# Check cluster access
kubectl get nodes

# Check all data space pods
kubectl get pods --all-namespaces | grep -E "(authority|companyx|companyy)"

# Test endpoints
curl -k https://issuer.<DOMAIN>/.well-known/did.json
curl -k https://bdrs.<DOMAIN>/health
curl -k https://companyx.<DOMAIN>/api/v1/management/health
curl -k https://companyy.<DOMAIN>/api/v1/management/health

# Check DNS resolution
nslookup issuer.<DOMAIN>
nslookup bdrs.<DOMAIN>
nslookup companyx.<DOMAIN>
nslookup companyy.<DOMAIN>
```

## Best Practices

1. **Always backup state files** before major changes
2. **Use version control** for all Terraform configurations
3. **Document domain names** and other critical variables
4. **Test recovery procedures** in non-production environments
5. **Keep DID credentials** in a secure, backed-up location

## Emergency Recovery

If everything is broken:

1. **Identify what exists**: Use AWS Console/CLI to inventory resources
2. **Start with EKS layer**: Get the infrastructure state restored first
3. **Work layer by layer**: Don't try to fix everything at once
4. **Import systematically**: Import resources one by one if needed
5. **Document changes**: Keep track of what you import/modify

## Getting Help

If you encounter issues not covered in this guide:

- Check the main `CLAUDE.md` file for project-specific configurations
- Review Terraform documentation for import procedures
- Use `terraform state list` to see what's currently in state
- Use `kubectl get all --all-namespaces` to see what exists in the cluster