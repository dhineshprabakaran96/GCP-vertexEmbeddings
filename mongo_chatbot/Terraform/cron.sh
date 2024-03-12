#!/bin/bash

while true; do
    # Get a new access token
    ACCESS_TOKEN=$(gcloud auth print-access-token)

    # Update the environment variable in the Cloud Run service
    gcloud run services update webex-bot-genapp --region=us-central1 --update-env-vars GCLOUD_ACCESS_TOKEN="$ACCESS_TOKEN"

    # Wait for 30 minutes
    sleep 30000
done
