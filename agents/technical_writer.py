from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class TechnicalWriter(BaseAgent):
    def __init__(self):
        super().__init__(
            role="technicalWriter",
            goal="Create clear and comprehensive technical documentation.",
            backstory="Expert in technical writing, documentation, and knowledge management."
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
        prompt = f"""You are an expert Technical Writer specializing in creating clear and comprehensive technical documentation.
        Your expertise includes technical writing, API documentation, user guides, and knowledge management.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on technical writing best practices,
        documentation structure, content organization, and practical implementation guidance. Include specific
        writing techniques, documentation tools, and content management strategies when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
