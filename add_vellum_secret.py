#!/usr/bin/env python3
"""
Script to add Vellum GitHub secret to repository
"""

import subprocess
import json
import sys
import os

# Repository and secret details
REPO_OWNER = "rpriddy7-alt"
REPO_NAME = "IWMcallsONLY"
SECRET_NAME = "GIT"
SECRET_VALUE = "pr_C61vs7YHkRTi"

def add_github_secret():
    """Add the Vellum secret to GitHub repository"""
    
    print("🔧 Adding Vellum secret to GitHub repository...")
    print(f"   Repository: {REPO_OWNER}/{REPO_NAME}")
    print(f"   Secret Name: {SECRET_NAME}")
    print(f"   Secret Value: {SECRET_VALUE[:10]}... (hidden)")
    
    # First check if gh CLI is available
    try:
        result = subprocess.run(["which", "gh"], capture_output=True, text=True)
        if result.returncode != 0:
            print("\n❌ GitHub CLI (gh) is not installed.")
            print("\n📝 To add the secret manually:")
            print(f"1. Go to: https://github.com/{REPO_OWNER}/{REPO_NAME}/settings/secrets/actions")
            print("2. Click 'New repository secret'")
            print(f"3. Name: {SECRET_NAME}")
            print(f"4. Value: {SECRET_VALUE}")
            print("5. Click 'Add secret'\n")
            
            print("Or install GitHub CLI and run this script again:")
            print("   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg")
            print("   echo 'deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main' | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null")
            print("   sudo apt update && sudo apt install gh")
            return False
    except:
        pass
    
    # Try to authenticate with gh
    auth_check = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if auth_check.returncode != 0:
        print("\n❌ Not authenticated with GitHub CLI.")
        print("\n📝 Please authenticate first:")
        print("   gh auth login")
        print("\nThen run this script again.")
        return False
    
    # Add the secret using gh CLI
    try:
        cmd = [
            "gh", "secret", "set", SECRET_NAME,
            "--body", SECRET_VALUE,
            "--repo", f"{REPO_OWNER}/{REPO_NAME}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ Successfully added secret '{SECRET_NAME}' to repository!")
            print(f"   This secret is now available for Vellum integration.")
            return True
        else:
            print(f"\n❌ Failed to add secret: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def create_vellum_config():
    """Create a Vellum configuration file"""
    vellum_config = {
        "repository": f"https://github.com/{REPO_OWNER}/{REPO_NAME}",
        "branch": "IWM-MAIN",
        "secret_name": SECRET_NAME,
        "integration": "vellum",
        "description": "Vellum AI integration for IWM momentum trading system"
    }
    
    with open('.vellum/config.json', 'w') as f:
        json.dump(vellum_config, f, indent=2)
    
    print("\n📄 Created .vellum/config.json for Vellum integration")

if __name__ == "__main__":
    # Create .vellum directory if it doesn't exist
    os.makedirs('.vellum', exist_ok=True)
    
    # Add the secret
    success = add_github_secret()
    
    if success:
        create_vellum_config()
        print("\n🎉 Vellum integration setup complete!")
        print("   Your repository is now connected to Vellum.")
    else:
        print("\n⚠️  Please follow the manual instructions above to complete setup.")
