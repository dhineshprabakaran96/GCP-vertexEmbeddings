module "cloud_run" {
  source                = "git@github.ford.com:gcp/tfm-cloud-run.git"
  gcp_project_id        = "ford-4360b648e7193d62719765c7" # The id of the project where the cloud run service is to be deployed"
  service_name          = "webex-bot"      # The name of the cloud run service"
  service_image_url     = "us-central1-docker.pkg.dev/ford-4360b648e7193d62719765c7/ford-container-images/genapp-bot:1.0"
  gcp_region            = "us-central1"
  service_account_email = "sa-chatgpt-run@ford-4360b648e7193d62719765c7.iam.gserviceaccount.com"                                                                     # This service account represents the identity of the service and determines what permissions the service has.
  service_invoker       = ["allUsers"]   
  service_vpc_connector = "projects/prj-pp-gen-preprod-net-acc7/locations/us-central1/connectors/preprod-gen-central1"      
  timeout_seconds       = 3600
  min_instance_count    = 1
  # memory_size           = 8000
  environment = [ # List of environment variables to set in the container.
    {
      name  = "project_id"
      value = "ford-4360b648e7193d62719765c7"
    },
    {
      name  = "GCLOUD_ACCESS_TOKEN" 
      value = ""
    },
    {
      name  = "BOT_ACCESS_TOKEN" 
      value = ""
    },
    {
      name  = "ORG_ID" 
      value = ""
    },
    {
      name  = "webhook_secret" 
      value = ""
    }
  ]
}