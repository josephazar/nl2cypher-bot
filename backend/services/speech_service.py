"""
Service for interacting with Azure Speech Services.
"""
import os
import requests
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SpeechService:
    """Service for Azure Speech Services"""
    
    def __init__(self):
        """Initialize the SpeechService"""
        self.region = os.getenv("AZURE_SPEECH_REGION", "westeurope")
        self.subscription_key = os.getenv("AZURE_SPEECH_KEY")
        
        # The standard format for Azure Speech token endpoint
        # There are different regional endpoints in Azure, try both common patterns
        standard_endpoint = f"https://{self.region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
        
        # Some regions may use a different format
        # Modified endpoint for regions that might use a different pattern
        alternate_endpoint = None
        if "." not in self.region:  # It's a simple region name, not a full domain
            alternate_endpoint = f"https://{self.region}.sts.speech.microsoft.com/issuetoken" 
        
        # Try to use a provided endpoint from env vars first
        endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")
        if endpoint:
            # Check if endpoint already ends with the token path
            if not endpoint.endswith("/issuetoken"):
                # Remove trailing slash if present
                if endpoint.endswith("/"):
                    endpoint = endpoint[:-1]
                # Add the token path
                if "/sts/" in endpoint.lower():
                    endpoint = f"{endpoint}/issuetoken"
                else:
                    endpoint = f"{endpoint}/sts/v1.0/issuetoken"
        else:
            # No endpoint provided, use standard
            endpoint = standard_endpoint
            
        self.endpoint = endpoint
        self.alternate_endpoint = alternate_endpoint
        logger.info(f"Speech service primary endpoint: {self.endpoint}")
        if alternate_endpoint:
            logger.info(f"Speech service alternate endpoint: {self.alternate_endpoint}")
        self.token_expiry = None
        self.token = None
        
    def get_token(self) -> str:
        """
        Get an authentication token for Azure Speech Services
        
        Returns:
            Authentication token as a string
        """
        # Check if we already have a valid token
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            logger.info("Using cached speech token (valid until %s)", self.token_expiry)
            return self.token
            
        # Request a new token
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key
        }
        
        try:
            logger.info("Requesting new speech token from: %s", self.endpoint)
            logger.info("Using subscription key: %s", self.subscription_key[:4] + '...' if self.subscription_key else "None")
            
            response = requests.post(self.endpoint, headers=headers)
            logger.info("Token response status: %s", response.status_code)
            
            if response.status_code != 200:
                logger.error("Error response: %s", response.text)
                
                # If primary endpoint fails and we have an alternate, try that
                if self.alternate_endpoint and response.status_code == 404:
                    logger.info("Primary endpoint failed. Trying alternate endpoint: %s", self.alternate_endpoint)
                    alt_response = requests.post(self.alternate_endpoint, headers=headers)
                    
                    if alt_response.status_code == 200:
                        # Success with alternate endpoint - save it as primary for future
                        logger.info("Alternate endpoint successful. Status: %s", alt_response.status_code)
                        self.endpoint = self.alternate_endpoint
                        
                        # Store the token with an expiry time (10 minutes is typical)
                        self.token = alt_response.text
                        self.token_expiry = datetime.now() + timedelta(minutes=9)  # Set expiry to 9 minutes to be safe
                        
                        logger.info("Generated new Azure Speech token (expiry: %s)", self.token_expiry)
                        logger.info("Token: %s...", self.token[:10] if self.token else "None")
                        return self.token
                    else:
                        logger.error("Alternate endpoint also failed. Status: %s", alt_response.status_code)
                        logger.error("Alternate endpoint error: %s", alt_response.text)
                
                raise Exception(f"Token request failed with status {response.status_code}: {response.text}")
                
            response.raise_for_status()
            
            # Store the token with an expiry time (10 minutes is typical)
            self.token = response.text
            self.token_expiry = datetime.now() + timedelta(minutes=9)  # Set expiry to 9 minutes to be safe
            
            logger.info("Generated new Azure Speech token (expiry: %s)", self.token_expiry)
            logger.info("Token: %s...", self.token[:10] if self.token else "None") 
            return self.token
            
        except Exception as e:
            logger.error(f"Error getting Azure Speech token: {str(e)}")
            raise  

    
    def get_token_for_frontend(self) -> Dict[str, Any]:
        """
        Get token and configuration information for the frontend
        
        Returns:
            Dictionary with token and configuration information
        """
        try:
            token = self.get_token()
            
            result = {
                'token': token,
                'region': self.region,
                'language': 'fr-FR',  # Default to French, can be made configurable
                'endpointId': ''  # Custom endpoint ID if needed
            }
            
            logger.info(f"Frontend speech token generated successfully, region: {self.region}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating frontend speech token: {str(e)}")
            return {
                'token': '',
                'region': self.region or '',
                'language': 'fr-FR',
                'error': str(e)
            }