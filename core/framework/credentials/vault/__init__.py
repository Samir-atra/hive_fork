"""
Vault integration for the credential store.

This module provides enterprise-grade secret management through
HashiCorp Vault and Azure Key Vault integration.

Quick Start (HashiCorp Vault):
    from core.framework.credentials import CredentialStore
    from core.framework.credentials.vault import HashiCorpVaultStorage

    # Configure Vault storage
    storage = HashiCorpVaultStorage(
        url="https://vault.example.com:8200",
        # token read from VAULT_TOKEN env var
        mount_point="secret",
        path_prefix="hive/agents/prod"
    )

    # Create credential store with Vault backend
    store = CredentialStore(storage=storage)

    # Use normally - credentials are stored in Vault
    credential = store.get_credential("my_api")

Quick Start (Azure Key Vault):
    from core.framework.credentials import CredentialStore
    from core.framework.credentials.vault import AzureKeyVaultStorage

    # Configure Azure Key Vault storage
    storage = AzureKeyVaultStorage(
        vault_url="https://my-vault.vault.azure.net",
        secret_prefix="hive-credentials"
    )

    # Create credential store with Azure Key Vault backend
    store = CredentialStore(storage=storage)

    # Use normally - credentials are stored in Azure Key Vault
    credential = store.get_credential("my_api")

Requirements:
    HashiCorp Vault: pip install hvac
    Azure Key Vault: pip install azure-identity azure-keyvault-secrets

Authentication (HashiCorp Vault):
    Set the VAULT_TOKEN environment variable or pass the token directly:

        export VAULT_TOKEN="hvs.xxxxxxxxxxxxx"

    For production, consider using Vault auth methods:
    - Kubernetes auth
    - AppRole auth
    - AWS IAM auth

Authentication (Azure Key Vault):
    The adapter uses DefaultAzureCredential which supports multiple methods:
    1. Environment variables (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
    2. Managed Identity (when running in Azure)
    3. Azure CLI (az login)
    4. Visual Studio Code
    5. Interactive browser

Vault Configuration (HashiCorp):
    Ensure KV v2 secrets engine is enabled:

        vault secrets enable -path=secret kv-v2

    Grant appropriate policies:

        path "secret/data/hive/credentials/*" {
            capabilities = ["create", "read", "update", "delete", "list"]
        }
        path "secret/metadata/hive/credentials/*" {
            capabilities = ["list", "delete"]
        }

Azure Setup (Azure Key Vault):
    1. Create a Key Vault:
        az keyvault create --name my-vault --resource-group my-rg

    2. Grant your identity access:
        az keyvault set-policy --name my-vault --spn <your-client-id> \\
            --secret-permissions get set list delete

    3. For Managed Identity (recommended for production):
        # Create a user-assigned managed identity
        az identity create --name my-identity --resource-group my-rg

        # Grant the identity access to Key Vault
        az keyvault set-policy --name my-vault --object-id <identity-principal-id> \\
            --secret-permissions get set list delete
"""

from .hashicorp import HashiCorpVaultStorage

# Lazy import to avoid requiring azure-identity when not used
try:
    from .azure import AzureKeyVaultStorage

    _AZURE_AVAILABLE = True
except ImportError:
    _AZURE_AVAILABLE = False
    AzureKeyVaultStorage = None  # type: ignore[misc,assignment]

__all__ = ["HashiCorpVaultStorage", "AzureKeyVaultStorage"]

# Track Azure availability for runtime checks
AZURE_AVAILABLE = _AZURE_AVAILABLE
