import weaviate

auth_config = weaviate.AuthApiKey(api_key="RbZZuIxHnoxq3LpfCerCP4h4q5684PuskBEE")

client = weaviate.Client(
  url="https://ford-astronomer-astrobot-3tdrhgxk.weaviate.network",
  auth_client_secret=auth_config
)