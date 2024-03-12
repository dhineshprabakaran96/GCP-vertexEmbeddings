from google.cloud import secretmanager

# Define the name of the secret
secret_name = "projects/my-project/secrets/my-secret/versions/latest"

# Fetch the secret value
def get_secret():
    # Create a client object
    client = secretmanager.SecretManagerServiceClient()

    try:
        # Fetch the secret version
        response = client.access_secret_version(name=secret_name)
        # Decode the secret value from bytes to string
        secret_value = response.payload.data.decode("UTF-8")
        return secret_value

    except Exception as e:
        print(f"Error fetching secret: {e}")
        return None

# Call the function to get the secret value
secret_value = get_secret()

# Use the secret value in your code
if secret_value:
    print(f"The secret value is: {secret_value}")
else:
    print("Failed to fetch secret value")
