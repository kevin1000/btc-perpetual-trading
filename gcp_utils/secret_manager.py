# gcp_utils/secret_manager.py
from google.cloud import secretmanager

class GCPManager:
    def __init__(self, project_id):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id

    def access_secret_version(self, secret_id, version_id="latest"):
        # Build the resource name of the secret version.
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"

        # Access the secret version.
        response = self.client.access_secret_version(request={"name": name})

        # Return the decoded payload.
        return response.payload.data.decode('UTF-8')

