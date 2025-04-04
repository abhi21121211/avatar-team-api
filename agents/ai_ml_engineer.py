from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class aIMLEngineer(BaseAgent):
    def __init__(self):
        super().__init__(
            role="AI/MLEngineer",
            goal="Design and implement machine learning and AI solutions.",
            backstory="Expert in machine learning algorithms, neural networks, and data science."
        )
    
    def _generate_response(self, message, context):
        """Generate a response based on the message and context using Gemini API"""
        # Get context from other agents
        other_context = ""
        for agent, convos in context["all_conversations"].items():
            if agent != self.role and convos:
                latest = convos[-1]
                other_context += f"{agent} discussed: {latest['user_message']} - {latest['agent_response']}\n"
        
        # Create a professional prompt for Gemini
        prompt = f"""You are an expert AI/ML Engineer specializing in machine learning, deep learning, and artificial intelligence.
        Your expertise includes neural networks, data science, model optimization, and AI system architecture.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on AI/ML best practices,
        model selection, training strategies, and practical implementation guidance. Include specific
        technical details, algorithm recommendations, and performance optimization tips when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
