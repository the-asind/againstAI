import logging
from typing import Dict, Type

from config import AI_SERVICE_TYPE
from services.ai.base_service import BaseAIService
from services.ai.gemini_service import GeminiService


SERVICE_CLASSES: Dict[str, Type[BaseAIService]] = {
    "gemini": GeminiService,
}

class AIServiceFactory:
    """Factory for creating AI service instances"""
    
    @staticmethod
    def create_service() -> BaseAIService:
        """
        Creates an AI service instance based on configuration
        
        Returns:
            BaseAIService: AI service instance
        """
        logger = logging.getLogger(__name__)
        
        
        service_type = AI_SERVICE_TYPE.lower()
        
        
        if service_type not in SERVICE_CLASSES:
            logger.warning(f"Unsupported AI service type: {service_type}. Using gemini as fallback.")
            service_type = "gemini"
        
        
        logger.info(f"Creating AI service of type: {service_type}")
        service_class = SERVICE_CLASSES[service_type]
        return service_class()
