# Deploying sample chatbot app in cloud run
 

### 1. Export Proxies and start Podman

```Text
export http_proxy=http://internet.ford.com:83  
export https_proxy=http://internet.ford.com:83

podman machine init
podman machine start

```

### 2. Build an image - Need to disconnect from VPN

```Text
podman build -t <image_name> .  # Here dot is required
```

### 2. Check whether the images is running in local

```Text
podman run -p 8084:8080 <image_name>:1.0 
```

### 3. Authenticate to us-central1-docker.pkg.dev:

```Text
gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images
 
gcloud auth print-access-token | podman login -u oauth2accesstoken --password-stdin gcr.io
```


### 4. Push the image into Artifact registry: (connect to VPN and enable proxy)

```Text
podman push us-central1-docker.pkg.dev/<project>/ford-container-images/<image name> --remove-signatures
```



### Example:
podman push us-central1-docker.pkg.dev/prj-cmsa-s-32c9/ford-container-images/ver1:1.0 --remove-signatures