# hubspot.py
import datetime
import json
import secrets
import requests
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import hashlib
import aiohttp
# Hey!!!!! Forgot to tell in video that I had also print the list_of_integration_item_metadata in the console(line 238) 
# as suggested in the assignment.

from integrations.integration_item import IntegrationItem

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

from fastapi import Request

CLIENT_ID = '6c389325-1d29-4072-a6f9-0a0ff019a51e'
CLIENT_SECRET = 'c6846518-2faa-430c-9491-8aca7ffc74d8'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()

scopes = 'crm.objects.users.read%20crm.objects.contacts.read%20settings.users.read' 
authorization_url = 'https://app.hubspot.com/oauth/authorize'


async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')

    code_verifier = secrets.token_urlsafe(32)
    m = hashlib.sha256()
    m.update(code_verifier.encode('utf-8'))
    code_challenge = base64.urlsafe_b64encode(m.digest()).decode('utf-8').replace('=', '')

    auth_url = f'{authorization_url}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scopes}&state={encoded_state}'

    await asyncio.gather(
        add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=6000),
        add_key_value_redis(f'hubspot_verifier:{org_id}:{user_id}', code_verifier, expire=6000),
    )
    return auth_url


async def oauth2callback_hubspot(request: Request):
    # Check for errors in the request parameters
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))

    # Retrieve code and state from the request
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))

    # Extract original state, user ID, and organization ID
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    # Retrieve the saved state and code verifier from Redis
    saved_state, code_verifier = await asyncio.gather(
        get_value_redis(f'hubspot_state:{org_id}:{user_id}'),
        get_value_redis(f'hubspot_verifier:{org_id}:{user_id}'),
    )

    # Verify the state matches the saved state to prevent CSRF attacks
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    # Exchange the authorization code for an access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.hubapi.com/oauth/v1/token",
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,  # HubSpot requires client_secret for token exchange
                'code_verifier': code_verifier,  # PKCE code verifier
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            }
        )

    if token_response.status_code != 200:
        print(f"Failed to obtain token: {token_response.text}")
        raise HTTPException(status_code=400, detail="Token exchange failed.")

    # Store the access token and other credentials in Redis
    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(token_response.json()), expire=6000)
    closeWindowScript = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authorization Successful</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background-color: #f5f5f5;
                text-align: center;
                font-family: Arial, sans-serif;
            }

            .container {
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .circle {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 150px;
                height: 150px;
                border-radius: 50%;
                border: 5px solid #4CAF50; /* Green border */
                margin-bottom: 20px;
            }

            .circle .checkmark {
                font-size: 100px;
                color: #4CAF50; /* Green tick */
            }


            .container p {
                font-size: 24px;
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="container">
        <div class="circle">
            <div class="checkmark">&#10003;</div>  <!-- Checkmark symbol -->
        </div>       
        <p>Authorization successful. You can close this window now.</p>
        </div>
        <script>
            window.close();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=closeWindowScript)


async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    
    # Check if credentials are found, otherwise raise an HTTPException
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    # Parse the credentials JSON string into a Python dictionary
    credentials = json.loads(credentials)
    
    # Delete the credentials from Redis after retrieval to maintain security
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    # Return the parsed credentials dictionary
    return credentials


def create_integration_item_metadata_object(
    response_json: dict, item_type: str, parent_id=None, parent_name=None
) -> IntegrationItem:
    # Create the IntegrationItem using response data
    integration_item_metadata = IntegrationItem(
        id=response_json.get('id', '') ,  
        name=response_json.get('firstName', None)+"_"+response_json.get('lastName', None), 
        email=response_json.get('email', None), 
        type=item_type,
    )

    return integration_item_metadata

# Function to fetch items recursively with pagination support
async def fetch_items(
    access_token: str, url: str, aggregated_response: list, after=None
) -> dict:
    """Fetching the list of contacts"""
    params = {'after': after} if after is not None else {}
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])  # 'results' is where HubSpot usually stores the items
                after = data.get('paging', {}).get('next', {}).get('after', None)

                for item in results:
                    aggregated_response.append(item)
                

                if after is not None:
                    await fetch_items(access_token, url, aggregated_response, after)
                
                else: return aggregated_response

# Function to get items from HubSpot
async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    credentials = json.loads(credentials)
    url = 'https://api.hubapi.com/settings/v3/users/'
    
    list_of_integration_item_metadata = []
    list_of_responses = []
    
    # Fetch contacts
    await fetch_items(credentials.get('access_token'), url, list_of_responses)
    
    async with aiohttp.ClientSession() as session:
        for response in list_of_responses:
            list_of_integration_item_metadata.append(
                create_integration_item_metadata_object(response, 'Contact')
            )


    print(f'list_of_integration_item_metadata: {list_of_integration_item_metadata}')
    return list_of_integration_item_metadata