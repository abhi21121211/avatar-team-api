import os
from typing import Dict, List, Optional, Union, Any

from utils.config import (
    ModelProvider,
    get_gemini_response,
    get_model_config
)

class LLMManager:
    """Class to manage LLM model configurations and settings"""
    
    def __init__(self):
        # Load default provider from environment variables
        self.default_provider: ModelProvider = os.getenv("DEFAULT_LLM_PROVIDER", "deepseek-chat")
        self.current_provider: ModelProvider = self.default_provider
        
        # Available models for each provider
        self.available_models: Dict[ModelProvider, List[str]] = {
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "deepseek": ["deepseek-chat", "deepseek-coder"],
            "llama3": ["llama-3-8b-chat", "llama-3-70b-chat"],
            "openrouter": ["openrouter/auto", "anthropic/claude-3-opus", "anthropic/claude-3-sonnet"],
            "openai": ["o3-mini", "gpt-4o", "gpt-4-turbo"]
        }
        
        # Current model for each provider
        self.current_models: Dict[ModelProvider, str] = {
            "gemini": "gemini-1.5-flash",
            "deepseek": "deepseek-chat",
            "llama3": "llama-3-70b-chat",
            "openrouter": "openrouter/auto",
            "openai": "o3-mini"
        }
    
    def get_available_providers(self) -> List[ModelProvider]:
        """Get list of available model providers"""
        return list(self.available_models.keys())
    
    def get_available_models(self, provider: Optional[ModelProvider] = None) -> List[str]:
        """Get available models for the specified provider"""
        if provider is None:
            provider = self.current_provider
        
        return self.available_models.get(provider, [])
    
    def set_provider(self, provider: ModelProvider) -> bool:
        """Set the current model provider"""
        if provider not in self.available_models:
            return False
        
        self.current_provider = provider
        return True
    
    def set_model(self, provider: ModelProvider, model: str) -> bool:
        """Set the current model for a specific provider"""
        if provider not in self.available_models or model not in self.available_models[provider]:
            return False
        
        self.current_models[provider] = model
        return True
    
    def get_current_provider(self) -> ModelProvider:
        """Get the current model provider"""
        return self.current_provider
    
    def get_current_model(self, provider: Optional[ModelProvider] = None) -> str:
        """Get the current model for the specified provider"""
        if provider is None:
            provider = self.current_provider
        
        return self.current_models.get(provider, "")
    
    def generate_response(self, prompt: str, provider: Optional[ModelProvider] = None, model: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response using the current or specified provider and model"""
        if provider is None:
            provider = self.current_provider
        
        if model is None:
            model = self.current_models.get(provider, "")
        
        try:
            # Add context to the prompt if provided
            enhanced_prompt = prompt
            if context:
                # Format context for the prompt
                context_str = ""
                if context.get("current_project"):
                    context_str += f"Current Project: {context['current_project']}\n"
                if context.get("role"):
                    context_str += f"Your Role: {context['role']}\n"
                if context.get("goal"):
                    context_str += f"Your Goal: {context['goal']}\n"
                
                # Only prepend context if it's not already included in the prompt
                if context_str and context_str not in prompt:
                    enhanced_prompt = f"{context_str}\n{prompt}"
            
            return get_gemini_response(enhanced_prompt, model=model, provider=provider)
        except Exception as e:
            return f"Error generating response with {provider}/{model}: {str(e)}"
    
    def get_provider_display_name(self, provider: ModelProvider) -> str:
        """Get a user-friendly display name for a provider"""
        display_names = {
            "gemini": "Google Gemini",
            "deepseek": "DeepSeek R1",
            "llama3": "Meta Llama 3",
            "openrouter": "OpenRouter",
            "openai": "OpenAI o3-mini"
        }
        return display_names.get(provider, provider)

# Create a singleton instance
llm_manager = LLMManager() 