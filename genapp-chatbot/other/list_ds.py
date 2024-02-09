    from google.cloud import discoveryengine_v1

    # Set your Google Cloud project, location, and data store ID
    project_id = "ford-4360b648e7193d62719765c7"
    location = "global"
    data_store_id = "astrobot_1697723843614"

    # Create a client
    client = discoveryengine_v1.DocumentServiceClient()

    # The full resource name of the data store.
    # e.g. projects/{project}/locations/{location}/dataStores/{data_store_id}
    datastore_name = f"projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/default_branch"

    with open("documents.txt", "w") as f:
        f.write(f"Documents in {data_store_id}:\n")

        response = client.list_documents(request={"parent": datastore_name})
        for document in response:
            f.write(str(document) + "\n")  
