from agents.base_agent import BaseAgent

class MarketingSales(BaseAgent):
    def __init__(self):
        super().__init__(
            role="marketing&Sales",
            goal="Handle B2B outreach & sales strategy.",
            backstory="Expert in digital marketing, lead generation, and enterprise sales."
        )
    
    def _generate_response(self, message, context):
        """Generate a response based on the message and context"""
        # In a real implementation, this would use an LLM
        # For now, we're using a simple response
        
        # Check if we have relevant context from other agents
        other_context = ""
        for agent, convos in context["all_conversations"].items():
            if agent != self.role and convos:
                latest = convos[-1]
                other_context += f"{agent} discussed: {latest['user_message']} - {latest['agent_response']}\n"
        
        if "campaign" in message.lower():
            return f"For marketing campaigns, I recommend a multi-channel approach aligned with our target audience personas. {other_context}"
        elif "market" in message.lower():
            return f"For market analysis, we should examine competition, trends, and customer needs to identify opportunities. {other_context}"
        elif "sales" in message.lower():
            return f"For sales strategies, I suggest focusing on value-based selling that aligns with customer needs. {other_context}"
        else:
            return f"As your marketing&Sales specialist, I'm here to help with marketing strategy and sales. What specific questions do you have? {other_context}"
