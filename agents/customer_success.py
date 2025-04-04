from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class CustomerSuccess(BaseAgent):
    def __init__(self):
        super().__init__(
            role="customerSuccess",
            goal="Ensure customer satisfaction and successful product adoption.",
            backstory="Expert in customer support, onboarding, and relationship management."
        )
    
    def _generate_response(self, message, context):
        """Generate a response based on the message and context using Gemini API"""
        # Get context from other agents
        other_context = ""
        for agent, convos in context["all_conversations"].items():
            if agent != self.role and convos:
                latest = convos[-1]
                other_context += f"{agent} discussed: {latest['user_message']} → {latest['agent_response']}\n"
        
        # Create a professional prompt for Gemini
        prompt = f"""You are an expert Customer Success Manager specializing in customer satisfaction and product adoption.
        Your expertise includes customer support, onboarding, relationship management, and customer success strategies.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on customer success best practices,
        onboarding strategies, support workflows, and practical implementation guidance. Include specific
        customer engagement techniques, success metrics, and relationship management approaches when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
