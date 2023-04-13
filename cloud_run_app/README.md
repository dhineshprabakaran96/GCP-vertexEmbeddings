# Deploying sample chatbot app in cloud run
 
Clone this repo and build the image - git clone https://github.ford.com/cmsa/ITO-ChatGPT

### 1. Export Proxies and start Podman

```Text
export http_proxy=http://internet.ford.com:83  
export https_proxy=http://internet.ford.com:83


podman machine init
podman machine start

```
### 2. Build an image - Need to disconnect from VPN

```Text
podman build -t <image_name>:1.0 .  # Here dot is required
```

### 3. Check whether the images is running in local

```Text
podman run -p 8084:8080 <image_name>:1.0 
```

### 4. Tag the image with a name:

```Text
podman tag localhost/<image_name>:1.0 us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images/ver1:1.0
```

### 5. Authenticate to us-central1-docker.pkg.dev:

```Text
gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images
 
gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin gcr.io
```


### 6. Push the image into Artifact registry: (connect to VPN and enable proxy)

```Text
podman push us-central1-docker.pkg.dev/<project>/ford-container-images/<image name> --remove-signatures
```

### Example:
```Text
podman build -t openai_chatbot_azure:1.0 .

podman run -p 8080:8080 openai_chatbot_azure:1.0 

podman tag localhost/openai_chatbot_azure:1.0 us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images/openai_chatbot_azure:1.0

gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images

gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin gcr.io

podman push us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images/openai_chatbot_azure:1.0 --remove-signatures
```

## Commom FAQs

1. Invoking a Cloud Run Service from an App or a Browser.
-> Checkout this link - https://pages.github.ford.com/serverless/serverless-hub/cloudrun/guides/invoking-cloud-run/#using-postman-for-api-based

2. Getting error "command not found: podman".
-> Install podman. - https://podman.io/getting-started/installation
