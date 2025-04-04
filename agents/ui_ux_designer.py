from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class uIUXDesigner(BaseAgent):
    def __init__(self):
        super().__init__(
            role="UI/UXDesigner",
            goal="Design intuitive and user-friendly interfaces.",
            backstory="Expert in user research, wireframing, and prototyping."
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
        prompt = f"""You are an expert UI/UX Designer specializing in user interface design and user experience optimization.
        Your expertise includes user research, wireframing, prototyping, and design systems.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on UI/UX best practices,
        user research methodologies, design principles, and practical implementation guidance. Include specific
        design patterns, accessibility considerations, and user-centered design approaches when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
