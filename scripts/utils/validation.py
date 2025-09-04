"""
Validation utilities for organization automation script.
"""
import re
import os
from pathlib import Path


def validate_org_name(org_name: str) -> bool:
    """
    Validate organization name.
    Must be lowercase, alphanumeric, and start with a letter.
    """
    if not org_name:
        return False
    
    pattern = r'^[a-z][a-z0-9]*$'
    return bool(re.match(pattern, org_name))


def validate_bpn(bpn: str) -> bool:
    """
    Validate Business Partner Number.
    Must follow format BPNL followed by 12 digits.
    """
    pattern = r'^BPNL\d{12}$'
    return bool(re.match(pattern, bpn))


def validate_domain(domain: str) -> bool:
    """
    Validate domain name.
    """
    if not domain:
        return False
    
    # Basic domain validation
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, domain))


def check_org_exists(org_name: str, deployment_dir: Path) -> bool:
    """
    Check if organization already exists by looking for Terraform files.
    """
    # Check for existing Terraform files with the organization name
    pattern = f"*{org_name}.tf"
    existing_files = list(deployment_dir.glob(pattern))
    
    return len(existing_files) > 0


def find_next_file_number(deployment_dir: Path) -> int:
    """
    Find the next available file number for organization Terraform files.
    """
    # Find all numbered terraform files (e.g., 2-companyx.tf, 3-companyy.tf)
    pattern = r'(\d+)-.*\.tf$'
    numbers = []
    
    for file_path in deployment_dir.glob("*.tf"):
        match = re.match(pattern, file_path.name)
        if match:
            numbers.append(int(match.group(1)))
    
    # Return next available number (skip 1 for authority, 4 for seed_data)
    if not numbers:
        return 2  # Start with 2 if no numbered files found
    
    next_num = max(numbers) + 1
    # Skip 4 if it's seed_data.tf
    if next_num == 4 and (deployment_dir / "4-seed_data.tf").exists():
        return 5
    
    return next_num


def get_existing_bpns(deployment_dir: Path) -> list:
    """
    Extract existing BPNs from variables.tf to avoid duplicates.
    """
    variables_file = deployment_dir / "variables.tf"
    existing_bpns = []
    
    if variables_file.exists():
        content = variables_file.read_text()
        # Look for BPN patterns in the file
        bpn_pattern = r'BPNL\d{12}'
        matches = re.findall(bpn_pattern, content)
        existing_bpns.extend(matches)
    
    return list(set(existing_bpns))  # Remove duplicates


def generate_next_bpn(existing_bpns: list) -> str:
    """
    Generate the next available BPN.
    """
    # Extract numbers from existing BPNs
    numbers = []
    for bpn in existing_bpns:
        if bpn.startswith('BPNL'):
            numbers.append(int(bpn[4:]))  # Extract number part after BPNL
    
    if not numbers:
        return "BPNL000000000001"  # Default first BPN
    
    next_num = max(numbers) + 1
    return f"BPNL{next_num:012d}"  # Format with leading zeros


def validate_deployment_directory(deployment_dir: Path) -> bool:
    """
    Validate that the deployment directory contains expected files.
    """
    required_files = [
        "variables.tf",
        "4-seed_data.tf",
        "terraform.tf"
    ]
    
    for file_name in required_files:
        if not (deployment_dir / file_name).exists():
            return False
    
    # Check for modules directory
    if not (deployment_dir / "modules").is_dir():
        return False
    
    return True