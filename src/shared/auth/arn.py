import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

_arn_cache = {}

def get_project_arn(project, secret_client=None):
    """
    Fetch the ACM Certificate ARN for the given project from Azure Key Vault, with in-memory caching.
    The project parameter is treated as dynamic; if the secret exists in Key Vault, the project is valid.
    """
    global _arn_cache
    secret_name = f"{project.lower()}-acm-arn"

    # Check in-memory cache first
    if _arn_cache.get(secret_name):
        return _arn_cache[secret_name]

    key_vault_url = os.environ.get('KEY_VAULT_URL')
    if not key_vault_url:
        raise Exception('KEY_VAULT_URL environment variable is not configured')

    if secret_client is None:
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

    try:
        arn = secret_client.get_secret(secret_name).value
        if not arn:
            raise Exception(f"Secret {secret_name} is empty in Key Vault")
        _arn_cache[secret_name] = arn  # Cache the ARN
        return arn
    except Exception as e:
        logging.error(f"Error retrieving ARN for {project} from Key Vault: {str(e)}")
        raise
