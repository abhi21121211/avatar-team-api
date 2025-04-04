from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response

class DevOpsEngineer(BaseAgent):
    def __init__(self):
        super().__init__(
            role="devOpsEngineer",
            goal="Manage CI/CD, cloud infrastructure, and monitoring.",
            backstory="Expert in cloud services, automation, and security best practices."
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
        prompt = f"""You are an expert DevOps Engineer specializing in cloud infrastructure, CI/CD, and automation.
        Your expertise includes containerization, Kubernetes, cloud platforms, and security best practices.
        
        Previous context from other team members:
        {other_context}
        
        User message: {message}
        
        Please provide a professional and detailed response focusing on DevOps best practices,
        infrastructure automation, CI/CD pipelines, and practical implementation guidance. Include specific
        technical details, tool recommendations, and security considerations when relevant."""
        
        # Get response from Gemini
        response = get_gemini_response(prompt)
        return response
