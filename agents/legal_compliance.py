from agents.base_agent import BaseAgent
from utils.config import get_gemini_response

class LegalCompliance(BaseAgent):
    def __init__(self, **data):
        data.update({
            "role": "legalCompliance",
            "goal": "Ensure legal compliance and data protection.",
            "backstory": "Expert in legal requirements, data privacy, and regulatory compliance."
        })
        super().__init__(**data)
    
    def _generate_response(self, message, context=None):
        """Generate a response based on the message and context using Gemini API"""
        # Get context from other agents
        other_context = ""
        if context and "all_conversations" in context:
            for agent, convos in context["all_conversations"].items():
                if agent != self.role and convos:
                    latest = convos[-1]
                    other_context += f"{agent} discussed: {latest['user_message']} → {latest['agent_response']}\n"
        
        # Create a professional prompt for Gemini
        prompt = f"""You are an expert Legal Compliance Officer specializing in legal requirements and data protection.
        Your expertise includes GDPR, data privacy, regulatory compliance, and legal risk management.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on legal compliance best practices,
        data protection requirements, regulatory frameworks, and practical implementation guidance. Include specific
        legal considerations, compliance strategies, and risk management approaches when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
