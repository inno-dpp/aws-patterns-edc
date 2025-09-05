"""
Terraform file manipulation utilities.
"""
import re
import json
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
    companies_pattern = r'(companies = \{.*?)(\n  \})'
    
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
    
    companies_replacement = rf'\1{new_company_entry}\2'
    content = re.sub(companies_pattern, companies_replacement, content, flags=re.DOTALL)
    
    # Add new participant DID local variable - insert before issuer_did
    participant_did_pattern = r'(  issuer_did               = "did:web:issuer\.\$\{local\.domain_name\}")'
    participant_did_replacement = rf'  {org_name}_participant_did = "did:web:{org_name}.${{local.domain_name}}"\n\1'
    
    content = re.sub(participant_did_pattern, participant_did_replacement, content)
    
    # Add new internal service locals - insert before seed_collections
    internal_service_pattern = r'(  seed_collections = \{)'
    internal_service_replacement = rf'''  {org_name}_ih_internal_service       = "${{lower(var.{org_name}_humanReadableName)}}-tractusx-identityhub"
  {org_name}_ih_internal_identity_port = 7081

\1'''
    
    content = re.sub(internal_service_pattern, internal_service_replacement, content)
    
    # Update BDRS seeding job to include new organization - add before BDRS_API_AUTH_KEY
    bdrs_env_vars_pattern = r'(            "--env-var", "BDRS_API_AUTH_KEY=\$\{var\.bdrs_api_auth_key\}")'
    bdrs_env_vars_replacement = rf'''            "--env-var", "{org_name.upper()}_DID=${{local.companies.{org_name}.participant_did}}",
            "--env-var", "{org_name.upper()}_BPN=${{var.{org_name}_bpn}}",
\1'''
    
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


def update_mvds_seed_json(seed_file: Path, org_name: str, bpn: str) -> None:
    """
    Update mvds-seed.json to include the new organization in the BDRS seeding.
    """
    with open(seed_file, 'r') as f:
        seed_data = json.load(f)
    
    # Find the SeedBDRS section
    seed_bdrs_section = None
    for item in seed_data.get("item", []):
        if item.get("name") == "SeedBDRS":
            seed_bdrs_section = item
            break
    
    if not seed_bdrs_section:
        raise ValueError("SeedBDRS section not found in mvds-seed.json")
    
    # Create new BPN mapping entry
    org_upper = org_name.upper()
    new_bpn_mapping = {
        "name": f"Create {org_name.title()} BPN Mapping",
        "event": [
            {
                "listen": "test",
                "script": {
                    "exec": [
                        "pm.test(\"Status code is 204\", function () {",
                        "    pm.response.to.have.status(204);",
                        "});"
                    ],
                    "type": "text/javascript",
                    "packages": {}
                }
            },
            {
                "listen": "prerequest",
                "script": {
                    "exec": [
                        ""
                    ],
                    "type": "text/javascript",
                    "packages": {}
                }
            }
        ],
        "request": {
            "method": "POST",
            "header": [],
            "body": {
                "mode": "raw",
                "raw": f'{{\n  "bpn": "{{{{{org_upper}_BPN}}}}",\n  "did": "{{{{{org_upper}_DID}}}}"\\n}}',
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            },
            "url": {
                "raw": "{{BDRS_MGMT_URL}}/bpn-directory",
                "host": [
                    "{{BDRS_MGMT_URL}}"
                ],
                "path": [
                    "bpn-directory"
                ]
            }
        },
        "response": []
    }
    
    # Add the new entry to the SeedBDRS items
    if "item" not in seed_bdrs_section:
        seed_bdrs_section["item"] = []
    
    seed_bdrs_section["item"].append(new_bpn_mapping)
    
    # Write back to file with proper formatting
    with open(seed_file, 'w') as f:
        json.dump(seed_data, f, indent=2)
        f.write('\n')  # Add trailing newline