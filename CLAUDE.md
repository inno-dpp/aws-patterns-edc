# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements a **Minimum Viable Data Space (MVDS)** on AWS for secure data sharing between organizations using Eclipse EDC (Dataspace Components) connectors. It demonstrates carbon emissions data exchange between two companies using the Eclipse Tractus-X variant of EDC with decentralized identity management.

## Architecture

The project uses a **two-tier Terraform deployment**:

1. **Infrastructure Layer** (`infrastructure/eks/`): Provisions Amazon EKS cluster with VPC, subnets, and required add-ons
2. **Application Layer** (`deployment/`): Deploys EDC connectors and data space components using Helm charts

**Key Components:**
- **Authority Namespace**: DID Issuer and BPN-DID Resolution Service (BDRS)
- **CompanyX Namespace**: Provider EDC connector with Tractus-X Identity Hub
- **CompanyY Namespace**: Consumer EDC connector with Tractus-X Identity Hub
- **Decentralized Identity**: Uses Eclipse DCP protocol with DIDs and Verifiable Credentials

## Directory Structure

```
├── infrastructure/eks/          # EKS cluster infrastructure (Terraform)
├── deployment/                  # Data space application deployment (Terraform + Helm)
│   ├── modules/                # Reusable Terraform modules for EDC components
│   └── assets/did/             # DID generation scripts and resources
├── data-sharing/api-collections/ # Postman collections for testing
└── carbon_emissions_data.json  # Sample data asset
```

## Development Commands

### Infrastructure Deployment

**EKS Infrastructure:**
```bash
cd infrastructure/eks
terraform init
terraform apply -var="domain_name=<YOUR_DOMAIN_NAME>"
aws eks update-kubeconfig --name aws-patterns-edc --region <AWS_REGION>
```

**Data Space Components:**
```bash
cd deployment
terraform init  
terraform apply
```

### DID Resource Generation

Before deploying data space components, generate required DID resources:
```bash
cd deployment/assets/did
python3 -m pip install -r requirements.txt
python3 jwt-gen.py --regenerate-keys --sign-jwts --domain <YOUR_DOMAIN_NAME> --assets-dir .
```

### Verification Commands

**Check EKS nodes:**
```bash
kubectl get nodes
```

**Verify data space pods:**
```bash
kubectl get pods --all-namespaces | grep -E "(authority|companyx|companyy|issuer|bdrs-server)"
```

**Test endpoints:**
```bash
nslookup issuer.<YOUR_DOMAIN_NAME>
nslookup companyx.<YOUR_DOMAIN_NAME>
nslookup companyy.<YOUR_DOMAIN_NAME>
curl -k https://companyx.<YOUR_DOMAIN_NAME>
```

### Cleanup

**Destroy in reverse order:**
```bash
# Data space components first
cd deployment
terraform destroy -auto-approve

# Then EKS infrastructure
cd ../infrastructure/eks  
terraform destroy -auto-approve
```

## Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform ~> 1.12.2
- kubectl 1.32+
- Python 3.8+ (for DID generation)
- Domain name with ACM certificate
- Route 53 hosted zone

## Configuration Notes

- **Default AWS Region**: eu-central-1 (configurable in `terraform.tfvars`)
- **Domain Requirements**: Must have ACM certificate and Route 53 hosted zone
- **Terraform Versions**: Uses specific provider versions for compatibility
- **State Management**: Uses local Terraform state with cross-references between layers
- **Security**: Default database passwords and API keys should be changed for production

## Testing

Use provided Postman collections in `data-sharing/api-collections/`:
- `companyx.postman_collection.json` - Provider connector operations
- `companyy.postman_collection.json` - Consumer connector operations

## Adding New Organizations

An automation script is available to simplify adding new organizations to the data space:

### Setup
```bash
cd scripts
python3 -m pip install -r requirements.txt
```

### Usage
```bash
# Add new organization with auto-generated BPN
python3 add-organization.py --org-name companyz --domain <YOUR_DOMAIN_NAME>

# Add with custom BPN  
python3 add-organization.py --org-name companyz --bpn BPNL000000000005 --domain <YOUR_DOMAIN_NAME>

# Preview changes without modifying files
python3 add-organization.py --org-name companyz --domain <YOUR_DOMAIN_NAME> --dry-run
```

### What the script does:
1. Creates Terraform configuration file (`N-organizationname.tf`)
2. Updates `variables.tf` with organization-specific variables
3. Updates `4-seed_data.tf` to include new organization in seeding process
4. Modifies `jwt-gen.py` to generate credentials for new organization
5. Creates organization-specific Postman collection

### After running the script:
1. Regenerate DID credentials: `python3 jwt-gen.py --regenerate-keys --sign-jwts --domain <DOMAIN> --assets-dir .`
2. Apply changes: `terraform plan && terraform apply`
3. Verify deployment: `kubectl get pods -n <org-namespace>`

## Component Versions

- Tractus-X Connector: 0.9.0
- Tractus-X Identity Hub: 0.8.0  
- Tractus-X BDRS Server: 0.5.2