"""
Terraform file manipulation utilities.
"""
import re
from pathlib import Path
from typing import List


def append_to_variables_tf(variables_file: Path, variables_content: str) -> None:
    """
    Append new variables to variables.tf file.
    """
    with open(variables_file, 'a') as f:
        f.write(f"\n{variables_content}\n")


def update_seed_data_tf(seed_data_file: Path, org_name: str, bpn: str) -> None:
    """
    Update 4-seed_data.tf to include the new organization.
    """
    content = seed_data_file.read_text()
    
    # Update seed_collections local - find the closing brace and add before it
    seed_collections_pattern = r'(seed_collections = \{[^}]*?companyy = kubernetes_namespace\.companyy_namespace\.metadata\[0\]\.name)(\s*\})'
    seed_collections_replacement = rf'\1\n    {org_name} = kubernetes_namespace.{org_name}_namespace.metadata[0].name\2'
    
    content = re.sub(seed_collections_pattern, seed_collections_replacement, content, flags=re.DOTALL)
    
    # Update companies local - add new company before the closing brace
    companies_pattern = r'(companies = \{[^}]*?companyy = \{[^}]*?\})(\s*\})'
    
    # Create new company entry
    new_company_entry = f'''
    {org_name} = {{
      namespace              = var.{org_name}_namespace
      participant_did        = "did:web:{org_name}.${{local.domain_name}}"
      participant_did_base64 = base64encode(local.{org_name}_participant_did)
      vc_membership_path     = "assets/did/{org_name}.membership.jwt"
      bpn                    = var.{org_name}_bpn
      ih_superuser_apikey    = var.{org_name}_ih_superuser_apikey
      module_dependency      = module.{org_name}_tx-identity-hub
      ih_internal_url        = "http://${{local.{org_name}_ih_internal_service}}:${{local.{org_name}_ih_internal_identity_port}}"
    }}'''
    
    companies_replacement = rf'\1{new_company_entry}\n  \2'
    content = re.sub(companies_pattern, companies_replacement, content, flags=re.DOTALL)
    
    # Add new participant DID local variable - insert after companyy_participant_did
    participant_did_pattern = r'(companyy_participant_did = "did:web:companyy\.\$\{local\.domain_name\}")'
    participant_did_replacement = rf'\1\n  {org_name}_participant_did = "did:web:{org_name}.${{local.domain_name}}"'
    
    content = re.sub(participant_did_pattern, participant_did_replacement, content)
    
    # Add new internal service locals - insert after companyy locals
    internal_service_pattern = r'(  companyy_ih_internal_identity_port = 7081)'
    internal_service_replacement = rf'''\1

  {org_name}_ih_internal_service       = "${{lower(var.{org_name}_humanReadableName)}}-tractusx-identityhub"
  {org_name}_ih_internal_identity_port = 7081'''
    
    content = re.sub(internal_service_pattern, internal_service_replacement, content)
    
    # Update BDRS seeding job to include new organization - add after companyy env vars
    bdrs_env_vars_pattern = r'("--env-var", "COMPANYY_BPN=\$\{var\.companyy_bpn\}")'
    bdrs_env_vars_replacement = rf'''\1,
            "--env-var", "{org_name.upper()}_DID=${{local.companies.{org_name}.participant_did}}",
            "--env-var", "{org_name.upper()}_BPN=${{var.{org_name}_bpn}}"'''
    
    content = re.sub(bdrs_env_vars_pattern, bdrs_env_vars_replacement, content)
    
    # Update first seed job dependencies - add new organization modules
    first_depends_on_pattern = r'(depends_on = \[module\.bdrs-server)(\])'
    first_depends_on_replacement = rf'\1,\n    module.{org_name}_tx-identity-hub,\n    module.{org_name}_connector_ingress\2'
    
    content = re.sub(first_depends_on_pattern, first_depends_on_replacement, content)
    
    # Update second seed job dependencies - add new organization modules  
    second_depends_on_pattern = r'(depends_on = \[[^\]]*module\.companyy_connector_ingress)(\s*\])'
    second_depends_on_replacement = rf'\1,\n    module.{org_name}_tx-identity-hub,\n    module.{org_name}_connector_ingress\2'
    
    content = re.sub(second_depends_on_pattern, second_depends_on_replacement, content, flags=re.DOTALL)
    
    seed_data_file.write_text(content)


def create_organization_tf(template_content: str, output_file: Path) -> None:
    """
    Create the organization Terraform file from template.
    """
    output_file.write_text(template_content)


def backup_file(file_path: Path) -> Path:
    """
    Create a backup of a file before modification.
    """
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
    backup_path.write_text(file_path.read_text())
    return backup_path


def validate_terraform_syntax(file_path: Path) -> bool:
    """
    Basic validation of Terraform syntax (checks for balanced braces).
    """
    content = file_path.read_text()
    
    # Count braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    
    return open_braces == close_braces


def find_terraform_files(directory: Path) -> List[Path]:
    """
    Find all Terraform files in the directory.
    """
    return list(directory.glob("*.tf"))