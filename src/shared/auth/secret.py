import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from typing import Dict, Any

_secrets_cache: Dict[str, Dict[str, str]] = {}


def get_cognito_credentials(project, secret_client=None):
    """Retrieve Cognito credentials from Azure Key Vault dynamically based on project."""

    # 1. Check if the project is already in the nested cache
    if project in _secrets_cache:
        return _secrets_cache[project]["client_id"], _secrets_cache[project]["client_secret"]

    try:
        key_vault_url = os.environ.get("KEY_VAULT_URL")

        # Dynamic secret resolution based on Project-ID
        client_id_secret_name = f"{project.lower()}-cognito-client-id"
        client_secret_secret_name = f"{project.lower()}-cognito-client-secret"

        if not key_vault_url:
            raise Exception("KEY_VAULT_URL environment variable is not configured")

        if secret_client is None:
            credential = DefaultAzureCredential()
            secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

        # Fetch from Key Vault

        client_id = secret_client.get_secret(client_id_secret_name).value
        client_secret = secret_client.get_secret(client_secret_secret_name).value

        # Type check to ensure both are str (not None)
        if not isinstance(client_id, str) or not isinstance(client_secret, str):
            raise TypeError("client_id and client_secret must be non-None strings")

        # 2. Store the result explicitly under the project name
        _secrets_cache[project] = {"client_id": client_id, "client_secret": client_secret}
        return client_id, client_secret

    except Exception as e:
        logging.error(f"Error retrieving credentials for {project} from Key Vault: {str(e)}")
        raise
