from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class FrontendEngineer(BaseAgent):
    def __init__(self):
        super().__init__(
            role="frontendEngineer",
            goal="Develop responsive and accessible web interfaces.",
            backstory="Expert in modern frontend frameworks like React, Next.js, and UI/UX best practices."
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
        prompt = f"""You are an expert Frontend Engineer specializing in modern web development. 
        Your expertise includes React, Next.js, and UI/UX best practices.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on frontend development best practices, 
        modern frameworks, and practical implementation advice. Include specific technical details and code examples when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
