import google.generativeai as genai
import logging
from typing import Dict, List, Tuple

from config import GEMINI_API_KEY
from models import Player, GameMode
from services.ai.base_service import BaseAIService


class GeminiService(BaseAIService):
    """Gemini API service implementation"""
    
    def __init__(self):
        super().__init__()
        
        try:
            
            genai.configure(api_key=GEMINI_API_KEY)
            
            
            available_models = [model.name for model in genai.list_models()]
            self.logger.info(f"Available models: {available_models}")
            
            
            model_name = None
            
            preferred_models = ["gemini-2.0-flash-lite"]
            for model in preferred_models:
                if any(model in m for m in available_models):
                    for full_name in available_models:
                        if model in full_name and "generateContent" in genai.get_model(full_name).supported_generation_methods:
                            model_name = full_name
                            break
                    if model_name:
                        break
            
            
            if not model_name:
                for full_name in available_models:
                    model = genai.get_model(full_name)
                    if "generateContent" in model.supported_generation_methods:
                        model_name = full_name
                        break
            
            if not model_name:
                raise ValueError("No suitable model found with generateContent support")
            
            self.model = genai.GenerativeModel(model_name)
            self.logger.info(f"Using model: {model_name}")
            
        except Exception as e:
            self.logger.error(f"Error initializing GeminiService: {e}", exc_info=True)
            
            self.model = None
            self.logger.warning("Using fallback mode without API access")
    
    async def evaluate_survival(self, scenario: str, players: Dict[int, Player], game_mode: GameMode) -> Tuple[str, List[int]]:
        """
        Evaluates player survival chances and generates a story
        
        Args:
            scenario: Game scenario
            players: Dictionary of players
            game_mode: Current game mode
            
        Returns:
            Tuple[str, List[int]]: Story narrative and list of survived player IDs
        """
        
        if game_mode == GameMode.BROTHERHOOD:
            prompt = self._build_cooperative_prompt(scenario, players)
        else:
            prompt = self._build_competitive_prompt(scenario, players)
            
        self.logger.info(f"Prompt created, length: {len(prompt)}")
        
        
        if not self.model:
            self.logger.warning("API unavailable, using fallback mode")
            return self._generate_fallback_response(scenario, players, game_mode)
        
        try:
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            
            if not response:
                self.logger.error("API returned empty response")
                return self._generate_fallback_response(scenario, players, game_mode)
            
            
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'parts'):
                parts = []
                for part in response.parts:
                    if hasattr(part, 'text'):
                        parts.append(part.text)
                    else:
                        parts.append(str(part))
                response_text = ''.join(parts)
            else:
                
                response_text = str(response)
            
            self.logger.info(f"Received response from API, length: {len(response_text)}")
            
            return response_text
        
        except Exception as e:
            self.logger.error(f"Error accessing Gemini API: {e}", exc_info=True)
            
            return self._generate_fallback_response(scenario, players, game_mode)
    