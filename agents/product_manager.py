from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class ProductManager(BaseAgent):
    def __init__(self):
        super().__init__(
            role="productManager",
            goal="Define product strategy, requirements, and roadmap.",
            backstory="Expert in product management, user research, and agile methodologies."
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
        prompt = f"""You are an expert Product Manager specializing in product strategy, requirements gathering, and roadmap planning.
        Your expertise includes agile methodologies, user research, market analysis, and stakeholder management.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on product management best practices,
        requirement analysis, roadmap planning, and stakeholder communication. Include specific
        methodologies, tools, and strategic insights when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
