import os
import httpx
import logging
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY")

# The direct Africa's Talking API endpoint for Sandbox SMS
# Currently using the Sandbox URL; switch to the production URL when ready.
AT_SMS_URL = "https://api.sandbox.africastalking.com/version1/messaging"

async def dispatch_emergency_sms(target_phone: str, message: str) -> dict:
    """
    Sends an outbound SMS using a native asynchronous HTTP request,
    bypassing the older SDK's SSL compatibility issues.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "apiKey": AT_API_KEY
    }
    
    payload = {
        "username": AT_USERNAME,
        "to": target_phone,
        "message": message
    }

    # httpx.AsyncClient handles the network call without blocking FastAPI
    # verify=False is used temporarily to bypass local Sandbox SSL mismatches
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(AT_SMS_URL, headers=headers, data=payload)
            
            # Check if the request was successful
            response.raise_for_status()
            response_data = response.json()
            
            logger.info(f"SMS successfully dispatched to {target_phone}. Response: {response_data}")
            return response_data
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to send SMS to {target_phone}. Network Error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {str(e)}")
            return {"error": str(e)}