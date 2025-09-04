"""
DID and JWT generation utilities.
"""
import re
from pathlib import Path
from typing import List


def update_jwt_gen_script(jwt_gen_path: Path, org_name: str, bpn: str) -> None:
    """
    Update jwt-gen.py to include the new organization.
    """
    content = jwt_gen_path.read_text()
    
    # Find the companies array and add new organization
    companies_pattern = r'(companies = \[[^\]]*?)(\s*\])'
    
    new_company_entry = f''',
        {{
            "filename": "{org_name}.membership.jwt",
            "holder_id": f"did:web:{org_name}.{{domain}}",
            "holder_identifier": "{bpn}"
        }}'''
    
    companies_replacement = rf'\1{new_company_entry}\2'
    content = re.sub(companies_pattern, companies_replacement, content, flags=re.DOTALL)
    
    jwt_gen_path.write_text(content)


def get_existing_organizations_from_jwt_gen(jwt_gen_path: Path) -> List[str]:
    """
    Extract existing organization names from jwt-gen.py.
    """
    content = jwt_gen_path.read_text()
    orgs = []
    
    # Find organization names in the companies array
    pattern = r'"filename":\s*"([a-z]+)\.membership\.jwt"'
    matches = re.findall(pattern, content)
    
    for match in matches:
        orgs.append(match)
    
    return orgs


def validate_jwt_gen_syntax(jwt_gen_path: Path) -> bool:
    """
    Basic validation of Python syntax in jwt-gen.py.
    """
    try:
        content = jwt_gen_path.read_text()
        compile(content, str(jwt_gen_path), 'exec')
        return True
    except SyntaxError:
        return False


def backup_did_assets(assets_dir: Path) -> Path:
    """
    Create backup of DID assets directory.
    """
    import shutil
    backup_dir = assets_dir.parent / f"{assets_dir.name}_backup"
    
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    
    shutil.copytree(assets_dir, backup_dir)
    return backup_dir