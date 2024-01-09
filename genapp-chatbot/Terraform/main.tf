module "cloud_run" {
  source                = "git@github.ford.com:gcp/tfm-cloud-run.git"
  gcp_project_id        = "ford-4360b648e7193d62719765c7" # The id of the project where the cloud run service is to be deployed"
  service_name          = "webex-bot-genapp"      # The name of the cloud run service"
  service_image_url     = "us-central1-docker.pkg.dev/ford-4360b648e7193d62719765c7/ford-container-images/genapp-bot:60.0"
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
      name  = "BOT_ACCESS_TOKEN" 
      value = "NjljNGJhMGItYzk3MC00OGQ5LWEzNTAtNjk0NTJjNWNlMTA0NDEzYzIzMTUtZTYw_PF84_af742d39-7515-46a3-82a7-03269e091b91"
    },
    {
      name = "INTEGRATION_ACCESS_TOKEN"
      value = "OGRkZTBjODUtN2U0NS00ZGY1LWEzZDItZTc4NjZkMjgwMjBlNjM1NzU0YTMtYzhm_PF84_af742d39-7515-46a3-82a7-03269e091b91"
    },
    {
      name  = "ORG_ID" 
      value = "Y2lzY29zcGFyazovL3VzL09SR0FOSVpBVElPTi9hZjc0MmQzOS03NTE1LTQ2YTMtODJhNy0wMzI2OWUwOTFiOTE"
    },
    {
      name  = "webhook_secret" 
      value = "QwsxErfvTyhnUik"
    },
    # {
    #   name  = "GCLOUD_ACCESS_TOKEN" 
    #   value = "ya29.a0AfB_byDsOK-j_G-HyASXo_K_GhFIi-08ooeeXYoFhlwAmTOJdgkKGO5d99YRKYRUrB10FQnYSqQEWFgoidUNlPopiSIIqPdtKmJLuHSEBYeR4D0bHhHNRqPQgI4tr9hvrCdDmgaM4ZyaSF1SILQtF-3XLUnqrjAsED3qrzsnVAaCgYKAdMSARESFQHGX2MitrQnY9e_igdbcWE97YaGTg0177"
    # },
    {
      name="CLIENT_ID"
      value= "b226389c-1320-3a29-c66b-aac5d043e18e"
    },
    {
      name="TERCES"
      value= "ZwTAbP4ZYPT-Zka_GexjILroY5hC-zuioCmliITw"
    }
  ]
}

