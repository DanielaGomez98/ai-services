import json
import requests
from typing import Dict, Any, Optional
from app.utils.logger.logger_util import get_logger

logger = get_logger()

INTERACTION_SERVICE_URL = "https://i8s5i8c21i.execute-api.us-east-1.amazonaws.com"

class InteractionClient:
    """Client for interacting with the external interaction service."""
    
    def __init__(self, base_url: str = INTERACTION_SERVICE_URL):
        self.base_url = base_url.rstrip('/')
        
    def track_interaction(
        self,
        user_id: str,
        user_input: Optional[str],
        ai_output: str,
        service_name: str = "text-mining",
        display_name: Optional[str] = None,
        service_description: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        response_time_seconds: Optional[float] = None,
        platform: str = "STAR"
    ) -> Optional[Dict[str, Any]]:
        """
        Track an AI interaction with the feedback service.
        
        Args:
            user_id: User identifier from frontend
            user_input: Original user request/document (optional)
            ai_output: AI-generated response (complete)
            service_name: Name of the AI service
            context: Service-specific context data
            response_time_seconds: Time taken to process
            platform: Platform identifier
            
        Returns:
            Response from feedback service or None if failed
        """
        try:
            payload = {
                "user_id": user_id,
                "ai_output": ai_output,
                "service_name": service_name,
                "display_name": display_name,
                "service_description": service_description,
                "context": context or {},
                "response_time_seconds": response_time_seconds,
                "platform": platform
            }
            
            # Add user_input only if provided
            if user_input:
                payload["user_input"] = user_input
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            logger.info(f"📝 Tracking interaction for service: {service_name}")
            logger.info(f"👤 User: {user_id}")
            logger.info(f"⏱️ Response time: {response_time_seconds}s")
            
            response = requests.post(
                f"{self.base_url}/api/interactions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Interaction tracked successfully: {result.get('interaction_id')}")
                return result
            else:
                logger.error(f"❌ Failed to track interaction: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("⏰ Timeout while tracking interaction")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 Network error while tracking interaction: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error while tracking interaction: {str(e)}")
            return None


interaction_client = InteractionClient()