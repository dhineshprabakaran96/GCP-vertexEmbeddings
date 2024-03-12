#!/usr/bin/env python

'''
This Program get you the Service account access token from WIF. Client_id,Secret,env,sa and project_number id will be input to run this program. 
Usage : python3 wif.py --client_id <client_id> --secret <secret> --env <dev|prod> --sa <your WIF SA> --project_number <your project_number>
example : python3 wif-dev.py --client_id 364f1f3f-49c3-7d46-2d59-7292cc034f0a --secret <secret of your adfs> --env prod --sa project-service-account@prj-compute-vm-images-pp-f378.iam.gserviceaccount.com --project_number 924036850941
'''

'''
CLI Command

 python3 auth.py --client_id b226389c-1320-3a29-c66b-aac5d043e18e --secret ZwTAbP4ZYPT-Zka_GexjILroY5hC-zuioCmliITw --env prod --sa "sa-chatgpt-run@ford-4360b648e7193d62719765c7.iam.gserviceaccount.com" --project_number 655678175973
'''

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import os
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import argparse

# parser = argparse.ArgumentParser(description='Getting Service account token')
# parser.add_argument('--client_id', type=str, required=True, help="client_id for ADFS app")
# parser.add_argument('--secret', type=str, required=True, help="Secret of ADFS app")
# parser.add_argument('--env', type=str, required=True, help="environment(example: dev or prod)")
# parser.add_argument('--sa', type=str, required=True, help="your service account (example: project-service-account@prj-os-hardened-d-b0de.iam.gserviceaccount.com )")
# parser.add_argument('--project_number', type=str, required=True, help="project_number(example: 462338243563)")

# args = parser.parse_args()

# # Settingup the variables

# Client_id=(args.client_id)
# Secret=(args.secret)
# env = (args.env)
# project_id = (args.project_number)
# sa = (args.sa)



Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]
env = "prod"
project_id = "655678175973"
sa = "sa-chatgpt-run@ford-4360b648e7193d62719765c7.iam.gserviceaccount.com"

identitypools="adfswif-pool"
provider="adfswif-provider"
scope_url="https://www.googleapis.com/auth/cloud-platform"

if env == "prod":
    adfs_url   = "https://corp.sts.ford.com/adfs/oauth2/token"
elif env == "dev":
    adfs_url   = "https://corpdev.sts.ford.com/adfs/oauth2/token"
else:
    print ("unsupported environement detected")

def adfs_auth(Client_id, Secret):
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        }
    resource_url="https://iam.googleapis.com/projects/{}/locations/global/workloadIdentityPools/{}/providers/{}".format(project_id,identitypools,provider)
    data = {
        "grant_type": "client_credentials",
        "response_type": "token",
        "client_id": Client_id,
        "client_secret": Secret,
        "resource": resource_url
    }
    response = requests.post(adfs_url, headers=headers, data=data, verify=False).json()
    acces_token = (response['access_token'])
    return(acces_token)

def wif_auth(Client_id, Secret ):
    subject_token=adfs_auth(Client_id, Secret)
    headers = {
        "Content-Type": "application/json",
        }
    audience_url="//iam.googleapis.com/projects/{}/locations/global/workloadIdentityPools/{}/providers/{}".format(project_id,identitypools,provider)
    data = '{{ "audience": "{}", "grantType": "urn:ietf:params:oauth:grant-type:token-exchange", "requestedTokenType": "urn:ietf:params:oauth:token-type:access_token", "scope": "{}", "subjectTokenType": "urn:ietf:params:oauth:token-type:jwt", "subjectToken": "{}" }}'.format(audience_url,scope_url,subject_token)
    wif_url="https://sts.googleapis.com/v1beta/token"
    response = requests.post(wif_url, headers=headers, data=data, verify=False).json()
    output = (response)
    return(output)

def fed_token(Client_id, Secret):
    output=wif_auth(Client_id, Secret )
    out=output['access_token']
    headers = {
    'Authorization': "Bearer " + out ,
    'Content-Type': 'application/json; charset=utf-8',
    }
    data = '{ "scope": [ "https://www.googleapis.com/auth/cloud-platform" ] }'
    fed_url='https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{}:generateAccessToken'.format(sa)
    response = requests.post(fed_url, headers=headers, data=data, verify=False).json()
    sa_token=response['accessToken']
    expiry_time=response['expireTime']
    return(sa_token, expiry_time)

def main():
    token=fed_token(Client_id, Secret)
    print(token)
    
if __name__ == "__main__":
    main()