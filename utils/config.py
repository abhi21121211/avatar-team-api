import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, Any, Optional, Literal

# Load environment variables from .env file
load_dotenv()

# Define model providers
ModelProvider = Literal["gemini", "deepseek", "llama3", "openrouter", "openai"]

def get_gemini_config():
    """Get Gemini API configuration"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Configure the Gemini API
    genai.configure(api_key=api_key)
    
    return {
        "api_key": api_key,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 2048,
    }

def get_deepseek_config():
    """Get DeepSeek API configuration"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
    
    return {
        "api_key": api_key,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
    }

def get_llama3_config():
    """Get Meta's Llama 3 API configuration"""
    api_key = os.getenv('LLAMA3_API_KEY')
    if not api_key:
        raise ValueError("LLAMA3_API_KEY not found in environment variables")
    
    return {
        "api_key": api_key,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
    }

def get_openrouter_config():
    """Get OpenRouter API configuration"""
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    return {
        "api_key": api_key,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
    }

def get_openai_config():
    """Get OpenAI API configuration"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    return {
        "api_key": api_key,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
    }

def get_model_config(provider: ModelProvider = "deepseek") -> Dict[str, Any]:
    """Get configuration for the specified model provider"""
    config_functions = {
        "gemini": get_gemini_config,
        "deepseek": get_deepseek_config,
        "llama3": get_llama3_config,
        "openrouter": get_openrouter_config,
        "openai": get_openai_config,
    }
    
    if provider not in config_functions:
        raise ValueError(f"Unsupported model provider: {provider}")
    
    return config_functions[provider]()

def get_gemini_response(prompt, model="gemini-1.5-flash", provider: ModelProvider = "deepseek"):
    """Generate a response from the specified model provider API"""
    
    if provider == "gemini":
        # Ensure API is configured
        config = get_gemini_config()
        
        # Create the model
        generation_model = genai.GenerativeModel(model)
        
        # Generate the response
        response = generation_model.generate_content(
            prompt,
            generation_config={
                "temperature": config["temperature"],
                "top_p": config["top_p"],
                "top_k": config["top_k"],
                "max_output_tokens": config["max_output_tokens"],
            }
        )
        
        return response.text
    
    # For other providers, use their respective APIs (to be implemented)
    elif provider == "deepseek":
        return get_response_from_deepseek(prompt)
    elif provider == "llama3":
        return get_response_from_llama3(prompt)
    elif provider == "openrouter":
        return get_response_from_openrouter(prompt)
    elif provider == "openai":
        return get_response_from_openai(prompt, model="o3-mini")
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

def get_response_from_deepseek(prompt: str) -> str:
    """Generate a response from DeepSeek API"""
    # TODO: Implement DeepSeek API integration
    import requests
    
    config = get_deepseek_config()
    
    # DeepSeek API URL (update with actual endpoint)
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",  # Update with appropriate model name
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "max_tokens": config["max_tokens"]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling DeepSeek API: {str(e)}")
        return f"Error generating response: {str(e)}"

def get_response_from_llama3(prompt: str) -> str:
    """Generate a response from Llama 3 API"""
    # TODO: Implement Llama 3 API integration
    import requests
    
    config = get_llama3_config()
    
    # Llama 3 API URL (update with actual endpoint)
    url = "https://api.meta.ai/v1/chat/completions"  # Update with correct endpoint
    
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3-70b-chat",  # Update with appropriate model name
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "max_tokens": config["max_tokens"]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling Llama 3 API: {str(e)}")
        return f"Error generating response: {str(e)}"

def get_response_from_openrouter(prompt: str) -> str:
    """Generate a response from OpenRouter API"""
    # TODO: Implement OpenRouter API integration
    import requests
    
    config = get_openrouter_config()
    
    # OpenRouter API URL
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "openrouter/auto",  # or specify a specific model
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "max_tokens": config["max_tokens"]
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Error calling OpenRouter API: {str(e)}")
        return f"Error generating response: {str(e)}"

def get_response_from_openai(prompt: str, model: str = "o3-mini") -> str:
    """Generate a response from OpenAI API"""
    # TODO: Implement OpenAI API integration
    import openai
    
    config = get_openai_config()
    
    # Configure OpenAI client
    openai.api_key = config["api_key"]
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=config["temperature"],
            top_p=config["top_p"],
            max_tokens=config["max_tokens"]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return f"Error generating response: {str(e)}" 