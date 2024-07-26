import asyncio
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import HttpRequest
import aiohttp

SCOPES = ['https://www.googleapis.com/auth/calendar']


async def get_calendar_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('creds/token.json'):
        creds = Credentials.from_authorized_user_file('creds/token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            asyncio.to_thread(creds.refresh, Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '/Users/hp/Documents/projects/lyfe/calendars/creds/gcal_creds.json', SCOPES)
            creds = await asyncio.to_thread(flow.run_local_server, port=0)
        # Save the credentials for the next run
        with open('creds/token.json', 'w') as token:
            token.write(creds.to_json())

    async def wrapped_request(request):
        return await asyncio.to_thread(request.execute)

    return build('calendar', 'v3', credentials=creds, requestBuilder=HttpRequest)
