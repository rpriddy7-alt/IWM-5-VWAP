#!/bin/bash

# GitHub repository details
OWNER="rpriddy7-alt"
REPO="IWMcallsONLY"
SECRET_NAME="GIT"
SECRET_VALUE="pr_C61vs7YHkRTi"

echo "==================================="
echo "GitHub Secret Setup for Vellum"
echo "==================================="
echo ""
echo "This will add the secret '$SECRET_NAME' to your repository for Vellum integration."
echo ""
echo "You need a GitHub Personal Access Token with 'repo' scope."
echo ""
echo "To create one:"
echo "1. Go to: https://github.com/settings/tokens/new"
echo "2. Give it a name (e.g., 'Vellum Integration')"
echo "3. Select scope: 'repo' (full control of private repositories)"
echo "4. Click 'Generate token'"
echo "5. Copy the token (it starts with 'ghp_')"
echo ""
read -p "Enter your GitHub Personal Access Token: " GITHUB_TOKEN

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

# Get repository public key for encrypting the secret
echo ""
echo "🔐 Getting repository public key..."
PUBLIC_KEY_RESPONSE=$(curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/secrets/public-key")

KEY_ID=$(echo $PUBLIC_KEY_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['key_id'])" 2>/dev/null)
PUBLIC_KEY=$(echo $PUBLIC_KEY_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['key'])" 2>/dev/null)

if [ -z "$KEY_ID" ] || [ -z "$PUBLIC_KEY" ]; then
    echo "❌ Failed to get repository public key."
    echo "Response: $PUBLIC_KEY_RESPONSE"
    echo ""
    echo "Make sure:"
    echo "1. Your token has the correct permissions"
    echo "2. The repository exists and you have access"
    exit 1
fi

echo "✅ Got public key"

# Encrypt the secret value
echo "🔒 Encrypting secret value..."
python3 << EOF
import base64
from nacl import encoding, public

public_key = "$PUBLIC_KEY"
secret_value = "$SECRET_VALUE"

# Decode the public key
public_key_decoded = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())

# Encrypt the secret value
sealed_box = public.SealedBox(public_key_decoded)
encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))

# Encode to base64
encrypted_base64 = base64.b64encode(encrypted).decode("utf-8")
print(encrypted_base64)
EOF > encrypted_value.txt

if [ ! -s encrypted_value.txt ]; then
    echo "❌ Failed to encrypt secret. Installing required Python library..."
    pip3 install PyNaCl --quiet
    
    # Try again
    python3 << EOF
import base64
from nacl import encoding, public

public_key = "$PUBLIC_KEY"
secret_value = "$SECRET_VALUE"

# Decode the public key
public_key_decoded = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())

# Encrypt the secret value
sealed_box = public.SealedBox(public_key_decoded)
encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))

# Encode to base64
encrypted_base64 = base64.b64encode(encrypted).decode("utf-8")
print(encrypted_base64)
EOF > encrypted_value.txt
fi

ENCRYPTED_VALUE=$(cat encrypted_value.txt)
rm encrypted_value.txt

if [ -z "$ENCRYPTED_VALUE" ]; then
    echo "❌ Failed to encrypt secret value"
    exit 1
fi

echo "✅ Secret encrypted"

# Add the secret to the repository
echo "📤 Adding secret to repository..."
RESPONSE=$(curl -s -X PUT \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/secrets/$SECRET_NAME" \
  -d "{\"encrypted_value\":\"$ENCRYPTED_VALUE\",\"key_id\":\"$KEY_ID\"}")

# Check if successful
if [ "$?" -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Secret '$SECRET_NAME' has been added to your repository!"
    echo ""
    echo "🔗 Vellum Integration Ready"
    echo "   Repository: https://github.com/$OWNER/$REPO"
    echo "   Secret Name: $SECRET_NAME"
    echo ""
    echo "The secret is now available for Vellum to use."
else
    echo "❌ Failed to add secret"
    echo "Response: $RESPONSE"
    exit 1
fi
