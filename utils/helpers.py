"""
Helper functions for the Avatar Team API.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def serialize_model(model: Any) -> Dict[str, Any]:
    """
    Serialize a Pydantic model to a dictionary.
    Works with both Pydantic v1 (dict) and v2 (model_dump).
    
    Args:
        model: A Pydantic model instance
        
    Returns:
        Dict representation of the model
    """
    try:
        # Try Pydantic v2 method first
        if hasattr(model, 'model_dump'):
            return model.model_dump()
        # Fall back to Pydantic v1 method
        elif hasattr(model, 'dict'):
            return model.dict()
        # For non-Pydantic objects, try to convert to dict
        elif hasattr(model, '__dict__'):
            return model.__dict__
        # If none of the above work, return the model as is
        else:
            return model
    except Exception as e:
        print(f"Error serializing model: {str(e)}")
        # Try manual conversion for common model types
        try:
            data = {}
            for attr in dir(model):
                # Skip private and special attributes
                if attr.startswith('_') or attr in ('dict', 'model_dump'):
                    continue
                    
                # Get attribute value
                value = getattr(model, attr)
                
                # Skip methods and callables
                if callable(value):
                    continue
                    
                # Serialize nested models
                if hasattr(value, 'dict') or hasattr(value, 'model_dump'):
                    data[attr] = serialize_model(value)
                # Handle lists of models
                elif isinstance(value, list):
                    data[attr] = [serialize_model(item) if hasattr(item, 'dict') or hasattr(item, 'model_dump') else item for item in value]
                # Handle datetimes
                elif isinstance(value, datetime):
                    data[attr] = value.isoformat()
                # Add other values directly
                else:
                    data[attr] = value
                    
            return data
        except Exception as nested_error:
            print(f"Manual serialization failed: {str(nested_error)}")
            # Last resort: convert to string
            return {"error": "Failed to serialize model", "model_str": str(model)} 