import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

_secrets_cache = {'client_id': None, 'client_secret': None}

def get_cognito_credentials(secret_client=None):
    """Retrieve Cognito credentials from Azure Key Vault (cached)"""
    if _secrets_cache['client_id'] and _secrets_cache['client_secret']:
        return _secrets_cache['client_id'], _secrets_cache['client_secret']

    try:
        key_vault_url = os.environ.get('KEY_VAULT_URL')
        client_id_secret_name = os.environ.get('COGNITO_CLIENT_ID_SECRET_NAME', 'cognito-client-id')
        client_secret_secret_name = os.environ.get('COGNITO_CLIENT_SECRET_SECRET_NAME', 'cognito-client-secret')

        if not key_vault_url:
            raise Exception('KEY_VAULT_URL environment variable is not configured')

        if secret_client is None:
            credential = DefaultAzureCredential()
            secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

        client_id = secret_client.get_secret(client_id_secret_name).value
        client_secret = secret_client.get_secret(client_secret_secret_name).value

        _secrets_cache['client_id'] = client_id
        _secrets_cache['client_secret'] = client_secret
        return client_id, client_secret
    except Exception as e:
        logging.error(f'Error retrieving credentials from Key Vault: {str(e)}')
        raise
