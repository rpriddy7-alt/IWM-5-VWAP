#!/usr/bin/env python3
"""
Add Vellum secret to GitHub repository
This script adds the GIT secret for Vellum integration
"""

import os
import json
import base64
import requests
from nacl import encoding, public

# Configuration
OWNER = "rpriddy7-alt"
REPO = "IWMcallsONLY"
SECRET_NAME = "GIT"
SECRET_VALUE = "pr_C61vs7YHkRTi"

def add_vellum_secret(token=None):
    """Add the Vellum secret to GitHub repository"""
    
    if not token:
        # Check for token in environment
        token = os.environ.get('GITHUB_TOKEN', '')
        
        if not token:
            print("❌ No GitHub token provided!")
            print("\nTo add the secret, you need a GitHub Personal Access Token:")
            print("1. Go to: https://github.com/settings/tokens/new")
            print("2. Name: 'Vellum Integration'")
            print("3. Select scope: 'repo'")
            print("4. Generate token")
            print("5. Run: GITHUB_TOKEN=<your-token> python3 vellum_secret.py")
            print("\nOr add manually at:")
            print(f"https://github.com/{OWNER}/{REPO}/settings/secrets/actions/new")
            print(f"Name: {SECRET_NAME}")
            print(f"Value: {SECRET_VALUE}")
            return False
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get public key
    print(f"🔐 Getting repository public key...")
    response = requests.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/public-key",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get public key: {response.status_code}")
        print(f"   {response.text}")
        return False
    
    key_data = response.json()
    key_id = key_data['key_id']
    public_key = key_data['key']
    
    print("✅ Got public key")
    
    # Encrypt the secret
    print("🔒 Encrypting secret...")
    public_key_decoded = public.PublicKey(
        public_key.encode("utf-8"), 
        encoding.Base64Encoder()
    )
    sealed_box = public.SealedBox(public_key_decoded)
    encrypted = sealed_box.encrypt(SECRET_VALUE.encode("utf-8"))
    encrypted_value = base64.b64encode(encrypted).decode("utf-8")
    
    print("✅ Secret encrypted")
    
    # Add the secret
    print(f"📤 Adding secret '{SECRET_NAME}' to repository...")
    response = requests.put(
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets/{SECRET_NAME}",
        headers=headers,
        json={
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
    )
    
    if response.status_code in [201, 204]:
        print(f"\n✅ SUCCESS! Secret '{SECRET_NAME}' has been added!")
        print(f"   Repository: https://github.com/{OWNER}/{REPO}")
        print(f"   Integration: Vellum AI")
        print("\n🎉 Vellum can now access your repository!")
        return True
    else:
        print(f"❌ Failed to add secret: {response.status_code}")
        print(f"   {response.text}")
        return False

if __name__ == "__main__":
    import sys
    
    # Check if token provided as argument
    token = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = add_vellum_secret(token)
    sys.exit(0 if success else 1)
