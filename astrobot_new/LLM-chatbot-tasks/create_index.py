from google.cloud import aiplatform

PROJECT_ID = "ford-071510988cc8f3cc7b39d2d8"
REGION = "us-central1" 

BUCKET_URI = "gs://astro-bot-bucket"  # @param {type:"string"}
UNIQUE_FOLDER_NAME = "astrobot-dp"
remote_folder = f"{BUCKET_URI}/{UNIQUE_FOLDER_NAME}/"

aiplatform.init(project=PROJECT_ID, location=REGION, staging_bucket=BUCKET_URI)


DISPLAY_NAME = "astrobot2602241300dp"
DESCRIPTION = "Questions from BMC KBAs"

# Create ANN index configuration
tree_ah_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name=DISPLAY_NAME,
    contents_delta_uri=remote_folder,
    dimensions=768,
    approximate_neighbors_count=150,
    distance_measure_type="DOT_PRODUCT_DISTANCE",
    leaf_node_embedding_count=500,
    leaf_nodes_to_search_percent=80,
    description=DESCRIPTION,
)

INDEX_RESOURCE_NAME = tree_ah_index.resource_name
print(INDEX_RESOURCE_NAME)


# Change bucket URL (if required)
# Change display name