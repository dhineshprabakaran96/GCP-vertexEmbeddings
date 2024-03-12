from google.cloud import aiplatform

PROJECT_ID = "ford-071510988cc8f3cc7b39d2d8"
REGION = "us-central1" 
BUCKET_URI = "gs://astro-bot-bucket" 

aiplatform.init(project=PROJECT_ID, location=REGION, staging_bucket=BUCKET_URI)

VPC_NETWORK_FULL = 'projects/870285755588/global/networks/vpc-c-vertex-hub'

DISPLAY_NAME = "astrobot2602241300indexep-dp"
DESCRIPTION = "Questions from BMC KBAs"

my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
    display_name=DISPLAY_NAME,
    description=DISPLAY_NAME,
    network=VPC_NETWORK_FULL,
)

INDEX_RESOURCE_NAME = 'projects/3711984193/locations/us-central1/indexes/8954532647770521600' #Change index ID
tree_ah_index = aiplatform.MatchingEngineIndex(index_name=INDEX_RESOURCE_NAME)

# Deploy IndexEndpoint

DEPLOYED_INDEX_ID = "astrobot2602241300dp"

my_index_endpoint = my_index_endpoint.deploy_index(
    index=tree_ah_index, deployed_index_id=DEPLOYED_INDEX_ID
)

print("Index Endpoint created!")
print(my_index_endpoint.deployed_indexes)


# Change bucket URI
# Change display name
# Change index ID