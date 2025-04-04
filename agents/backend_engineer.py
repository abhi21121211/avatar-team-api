from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class BackendEngineer(BaseAgent):
    def __init__(self):
        super().__init__(
            role="backendEngineer",
            goal="Design and implement robust, scalable API services and databases.",
            backstory="Expert in backend technologies, API design, and database optimization."
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
        prompt = f"""You are an expert Backend Engineer specializing in scalable and robust server-side development.
        Your expertise includes API design, database optimization, and backend architecture.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on backend development best practices,
        API design patterns, database optimization, and practical implementation advice. Include specific technical details
        and code examples when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
