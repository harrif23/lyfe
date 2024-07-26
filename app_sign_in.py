from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
from typing import Optional

app = FastAPI()

# Initialize Supabase client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


class AuthRequest(BaseModel):
    provider: str

class CallbackRequest(BaseModel):
    callback_url: str


@app.post("/auth/signin")
async def sign_in_with_provider(auth_request: AuthRequest):
    """
    Initiate the sign-in process with a social provider.
    """
    try:
        response = supabase.auth.sign_in_with_oauth({
            "provider": auth_request.provider,
            "options": {
                "redirect_to": "yourapp://callback"  # Replace with your app's callback URL
            }
        })
        return {"auth_url": response.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error initiating {auth_request.provider} sign-in: {str(e)}")


@app.post("/auth/callback")
async def handle_auth_callback(callback_request: CallbackRequest):
    """
    Handle the callback after social authentication.
    """
    try:
        response = supabase.auth.exchange_code_for_session(callback_request.callback_url)
        session = response.session
        if session and session.user:
            return {
                "user_id": session.user.id,
                "email": session.user.email,
                "provider": session.user.app_metadata.get("provider")
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to get user information")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error handling auth callback: {str(e)}")


@app.get("/user")
async def get_user(access_token: str):
    """
    Retrieve user information using the access token.
    """
    try:
        response = supabase.auth.get_user(access_token)
        user = response.user
        if user:
            return {
                "user_id": user.id,
                "email": user.email,
                "provider": user.app_metadata.get("provider")
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving user information: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

