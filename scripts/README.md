# Organization Automation Scripts

This directory contains automation scripts for adding new organizations to the AWS Data Space.

## Files

- `add-organization.py` - Main automation script
- `requirements.txt` - Python dependencies
- `templates/` - Jinja2 templates for file generation
- `utils/` - Utility modules for validation and file manipulation

## Usage

1. **Install dependencies:**
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. **Add a new organization:**
   ```bash
   # From repository root
   python3 scripts/add-organization.py --org-name companyz --domain your-domain.com
   
   # With custom BPN
   python3 scripts/add-organization.py --org-name companyz --bpn BPNL000000000005 --domain your-domain.com
   
   # Preview changes (dry run)
   python3 scripts/add-organization.py --org-name companyz --domain your-domain.com --dry-run
   ```

3. **After running the script:**
   ```bash
   # Generate DID credentials
   cd deployment/assets/did
   python3 jwt-gen.py --regenerate-keys --sign-jwts --domain your-domain.com --assets-dir .
   
   # Apply Terraform changes
   cd ../../
   terraform plan
   terraform apply
   
   # Verify deployment
   kubectl get pods -n companyz
   ```

## What the script does

1. **Validates inputs** - Checks organization name format, BPN format, domain validity
2. **Creates Terraform files** - Generates organization-specific Terraform configuration
3. **Updates configuration** - Modifies variables.tf and seed_data.tf
4. **Updates DID generation** - Adds new organization to jwt-gen.py
5. **Creates Postman collection** - Generates API testing collection

## Organization Requirements

- **Name**: Must be lowercase, alphanumeric, starting with a letter (e.g., "companyz")
- **BPN**: Business Partner Number in format BPNL + 12 digits (auto-generated if not provided)
- **Domain**: Valid domain name for the data space

## File Structure Created

For organization "companyz":
- `deployment/N-companyz.tf` - Terraform resources
- Updates to `deployment/variables.tf` - Variables configuration
- Updates to `deployment/4-seed_data.tf` - Seeding configuration
- Updates to `deployment/assets/did/jwt-gen.py` - DID generation
- `data-sharing/api-collections/companyz.postman_collection.json` - API collection

## Safety Features

- **Validation** - Comprehensive input validation
- **Dry run mode** - Preview changes before applying
- **Backup creation** - Automatically backs up modified files
- **Conflict detection** - Prevents duplicate organizations
- **BPN auto-increment** - Generates unique BPNs automatically