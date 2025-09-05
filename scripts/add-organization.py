#!/usr/bin/env python3
"""
Automation script for adding new organizations to the AWS Data Space.

This script automates the process of adding new organizations by:
1. Creating Terraform configuration files
2. Updating variables and seed data
3. Modifying DID generation scripts
4. Creating Postman collections
"""

import argparse
import sys
import json
from pathlib import Path
from jinja2 import Template

# Add utils to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from utils.validation import (
    validate_org_name, validate_bpn, validate_domain,
    check_org_exists, find_next_file_number, get_existing_bpns,
    generate_next_bpn, validate_deployment_directory
)
from utils.terraform_utils import (
    append_to_variables_tf, update_seed_data_tf,
    create_organization_tf, backup_file, update_mvds_seed_json
)
from utils.did_utils import update_jwt_gen_script


class OrganizationAutomator:
    """Main class for organization automation."""
    
    def __init__(self, args):
        self.args = args
        self.repo_root = script_dir.parent
        self.deployment_dir = self.repo_root / "deployment"
        self.templates_dir = script_dir / "templates"
        self.assets_dir = self.deployment_dir / "assets" / "did"
        self.data_sharing_dir = self.repo_root / "data-sharing" / "api-collections"
        self.seed_file = self.deployment_dir / "assets" / "seed" / "mvds-seed.json"
        
        self.backups = []  # Track backup files for rollback
        
    def validate_inputs(self) -> bool:
        """Validate all input parameters."""
        print("🔍 Validating inputs...")
        
        # Validate organization name
        if not validate_org_name(self.args.org_name):
            print("❌ Invalid organization name. Must be lowercase, alphanumeric, starting with letter.")
            return False
            
        # Validate BPN if provided
        if self.args.bpn and not validate_bpn(self.args.bpn):
            print("❌ Invalid BPN format. Must be BPNL followed by 12 digits.")
            return False
            
        # Validate domain
        if not validate_domain(self.args.domain):
            print("❌ Invalid domain name.")
            return False
            
        # Check if deployment directory exists and has required files
        if not validate_deployment_directory(self.deployment_dir):
            print("❌ Deployment directory is missing required files.")
            return False
            
        # Check if organization already exists
        if check_org_exists(self.args.org_name, self.deployment_dir):
            print(f"❌ Organization '{self.args.org_name}' already exists.")
            return False
            
        print("✅ Input validation passed.")
        return True
        
    def prepare_parameters(self) -> dict:
        """Prepare all parameters for template generation."""
        print("📋 Preparing parameters...")
        
        # Generate BPN if not provided
        existing_bpns = get_existing_bpns(self.deployment_dir)
        bpn = self.args.bpn or generate_next_bpn(existing_bpns)
        
        # Find next file number
        file_number = find_next_file_number(self.deployment_dir)
        
        params = {
            'org_name': self.args.org_name,
            'bpn': bpn,
            'domain': self.args.domain,
            'file_number': file_number
        }
        
        print(f"   Organization: {params['org_name']}")
        print(f"   BPN: {params['bpn']}")
        print(f"   Domain: {params['domain']}")
        print(f"   Terraform file number: {params['file_number']}")
        
        return params
        
    def create_terraform_files(self, params: dict) -> bool:
        """Create Terraform configuration files."""
        print("📝 Creating Terraform configuration files...")
        
        try:
            # Create organization Terraform file
            org_template_path = self.templates_dir / "organization.tf.j2"
            with open(org_template_path) as f:
                org_template = Template(f.read())
                
            org_content = org_template.render(**params)
            org_tf_file = self.deployment_dir / f"{params['file_number']}-{params['org_name']}.tf"
            
            if not self.args.dry_run:
                create_organization_tf(org_content, org_tf_file)
                
            print(f"   ✅ Created: {org_tf_file.name}")
            
            # Update variables.tf
            vars_template_path = self.templates_dir / "variables.tf.patch.j2"
            with open(vars_template_path) as f:
                vars_template = Template(f.read())
                
            vars_content = vars_template.render(**params)
            variables_file = self.deployment_dir / "variables.tf"
            
            if not self.args.dry_run:
                backup_file(variables_file)
                append_to_variables_tf(variables_file, vars_content)
                
            print(f"   ✅ Updated: variables.tf")
            
            # Update seed data
            seed_data_file = self.deployment_dir / "4-seed_data.tf"
            
            if not self.args.dry_run:
                backup_file(seed_data_file)
                update_seed_data_tf(seed_data_file, params['org_name'], params['bpn'])
                
            print(f"   ✅ Updated: 4-seed_data.tf")
            
            # Update mvds-seed.json
            if not self.args.dry_run:
                backup_file(self.seed_file)
                update_mvds_seed_json(self.seed_file, params['org_name'], params['bpn'])
                
            print(f"   ✅ Updated: assets/seed/mvds-seed.json")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating Terraform files: {e}")
            return False
            
    def update_did_generation(self, params: dict) -> bool:
        """Update DID generation script."""
        print("🔐 Updating DID generation script...")
        
        try:
            jwt_gen_file = self.assets_dir / "jwt-gen.py"
            
            if not self.args.dry_run:
                backup_file(jwt_gen_file)
                update_jwt_gen_script(jwt_gen_file, params['org_name'], params['bpn'])
                
            print(f"   ✅ Updated: jwt-gen.py")
            return True
            
        except Exception as e:
            print(f"❌ Error updating DID generation: {e}")
            return False
            
    def create_postman_collection(self, params: dict) -> bool:
        """Create Postman collection for the new organization."""
        print("📮 Creating Postman collection...")
        
        try:
            # Use companyx as template
            template_file = self.data_sharing_dir / "companyx.postman_collection.json"
            
            if not template_file.exists():
                print("   ⚠️ Template collection not found, skipping Postman collection.")
                return True
                
            with open(template_file) as f:
                collection_data = json.load(f)
                
            # Update collection for new organization
            collection_data["info"]["name"] = f"{params['org_name'].title()} Connector Management API"
            collection_data["info"]["description"] = f"API collection for {params['org_name']} connector operations"
            
            # Update variables
            for variable in collection_data.get("variable", []):
                if variable["key"] == "COMPANY_X_CONNECTOR_URL":
                    variable["key"] = f"{params['org_name'].upper()}_CONNECTOR_URL"
                    variable["value"] = f"https://{params['org_name']}.{params['domain']}"
                elif variable["key"] == "COMPANY_X_BPN":
                    variable["key"] = f"{params['org_name'].upper()}_BPN"
                    variable["value"] = params['bpn']
                    
            # Save new collection
            new_collection_file = self.data_sharing_dir / f"{params['org_name']}.postman_collection.json"
            
            if not self.args.dry_run:
                with open(new_collection_file, 'w') as f:
                    json.dump(collection_data, f, indent=2)
                    
            print(f"   ✅ Created: {new_collection_file.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating Postman collection: {e}")
            return False
            
    def print_next_steps(self, params: dict):
        """Print next steps for the user."""
        print("\n🎉 Organization setup completed!")
        print("\n📋 Next steps:")
        print("1. Regenerate DID credentials:")
        print(f"   cd deployment/assets/did")
        print(f"   python3 jwt-gen.py --regenerate-keys --sign-jwts --domain {params['domain']} --assets-dir .")
        
        print("\n2. Apply Terraform changes:")
        print("   cd deployment")
        print("   terraform plan")
        print("   terraform apply")
        
        print("\n3. Verify deployment:")
        print(f"   kubectl get pods -n {params['org_name']}")
        print(f"   nslookup {params['org_name']}.{params['domain']}")
        
        print(f"\n4. Import Postman collection:")
        print(f"   Import: data-sharing/api-collections/{params['org_name']}.postman_collection.json")
        
    def run(self) -> bool:
        """Run the organization automation process."""
        print(f"🚀 Adding organization '{self.args.org_name}' to AWS Data Space")
        
        if self.args.dry_run:
            print("🔍 DRY RUN MODE - No files will be modified")
            
        # Validate inputs
        if not self.validate_inputs():
            return False
            
        # Prepare parameters
        params = self.prepare_parameters()
        
        # Create files
        if not self.create_terraform_files(params):
            return False
            
        if not self.update_did_generation(params):
            return False
            
        if not self.create_postman_collection(params):
            return False
            
        # Print next steps
        if not self.args.dry_run:
            self.print_next_steps(params)
        else:
            print("\n🔍 DRY RUN COMPLETED - No files were modified")
            
        return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Automate adding new organizations to AWS Data Space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add new organization with auto-generated BPN
  python3 add-organization.py --org-name companyz --domain your-domain.com

  # Add with custom BPN
  python3 add-organization.py --org-name companyz --bpn BPNL000000000005 --domain your-domain.com

  # Dry run to preview changes
  python3 add-organization.py --org-name companyz --domain your-domain.com --dry-run
        """
    )
    
    parser.add_argument(
        "--org-name",
        required=True,
        help="Organization name (lowercase, alphanumeric, starting with letter)"
    )
    
    parser.add_argument(
        "--bpn",
        help="Business Partner Number (BPNL followed by 12 digits). Auto-generated if not provided."
    )
    
    parser.add_argument(
        "--domain",
        required=True,
        help="Domain name for the data space"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    
    args = parser.parse_args()
    
    # Run automation
    automator = OrganizationAutomator(args)
    success = automator.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()