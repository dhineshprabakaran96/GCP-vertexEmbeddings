import requests
import json

client_id = "7f159a11-92c2-4e68-a975-3d81617e893f"
client_secret = "xNtbklYSyuW5IkXMGHzE9Y73eLdVZfVjuyXxLBX97Tc="

def get_access_token(params):
    url = "https://accounts.accesscontrol.windows.net/c990bb7a-51f4-439b-bd36-9c07fb1041c0/tokens/OAuth/2"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=params)

    if response.status_code == 200:
        print("Access token generated!")
        return json.loads(response.text)["access_token"]
    else:
        print("Error ", response.status_code)
        return 0


def get_files_from_sharepoint(access_token, params):
    url = "https://azureford.sharepoint.com/sites/azure/_api/web/GetFileByServerRelativeUrl('/sites/azure/Shared%20Documents/Azure%20Subscription%20Naming%20Standard%20Guideline%20(1).docx')/$value"

    # payload='grant_type%20=client_credentials&client_id%20=0cb0e8ca-275e-4bb7-9eaf-08e599503401%40c990bb7a-51f4-439b-bd36-9c07fb1041c0&client_secret%20=8xt7mDIqBlqra5h6NCqLdHbuHmTqE6EYamg8PM9Pnnw%3D&resource=00000003-0000-0ff1-ce00-000000000000%2Fazureford.sharepoint.com%40c990bb7a-51f4-439b-bd36-9c07fb1041c0'
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("GET", url, headers=headers, data=params)

    if response.status_code == 200:
        with open('Feedback.doc', 'wb') as f:
            f.write(response.content)
        f.close()
        print("File downloaded from sharepoint")
    else:
        print("Error ", response.status_code)


def main():
    params = {
        "grant_type" : "client_credentials",
        "client_id" : client_id + "@c990bb7a-51f4-439b-bd36-9c07fb1041c0",
        "client_secret" : client_secret,
        "resource" : "00000003-0000-0ff1-ce00-000000000000/azureford.sharepoint.com@c990bb7a-51f4-439b-bd36-9c07fb1041c0"
    }

    access_token = get_access_token(params)

    get_files_from_sharepoint(access_token, params)


if __name__ == '__main__':
    main()