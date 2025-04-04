import os
import re

# Template for agent files
AGENT_TEMPLATE = """from agents.base_agent import BaseAgent

class {class_name}(BaseAgent):
    def __init__(self):
        super().__init__(
            role="{role}",
            goal="{goal}",
            backstory="{backstory}"
        )
    
    def _generate_response(self, message, context):
        \"\"\"Generate a response based on the message and context\"\"\"
        # In a real implementation, this would use an LLM
        # For now, we're using a simple response
        
        # Check if we have relevant context from other agents
        other_context = ""
        for agent, convos in context["all_conversations"].items():
            if agent != self.role and convos:
                latest = convos[-1]
                other_context += f"{{agent}} discussed: {{latest['user_message']}} → {{latest['agent_response']}}\\n"
        
{response_conditions}
        else:
            return f"As your {role}, I'm here to help with {domain}. What specific questions do you have? {{other_context}}"
"""

# Already updated agents
UPDATED_AGENTS = ['chief_architect.py', 'frontend_engineer.py', 'backend_engineer.py']

# Dictionary of role-specific responses
AGENT_RESPONSES = {
    "devOpsEngineer": {
        "domain": "DevOps and infrastructure",
        "conditions": [
            ("deployment", "For deployment strategies, I recommend using a CI/CD pipeline with automated testing and staged rollouts. {other_context}"),
            ("container", "For containerization, Docker with Kubernetes orchestration is the industry standard for scalable deployments. {other_context}"),
            ("pipeline", "For CI/CD pipelines, I recommend Jenkins or GitHub Actions depending on your existing infrastructure. {other_context}")
        ]
    },
    "AI/MLEngineer": {
        "domain": "AI and machine learning",
        "conditions": [
            ("model", "For model selection, I'd consider the specific requirements of your use case as well as computational constraints. {other_context}"),
            ("train", "For training machine learning models, I recommend using a pipeline that includes data validation, preprocessing, and performance monitoring. {other_context}"),
            ("data", "For data processing, we should establish a robust ETL pipeline with validation and versioning. {other_context}")
        ]
    },
    "productManager": {
        "domain": "product strategy and requirements",
        "conditions": [
            ("roadmap", "For product roadmap planning, I suggest aligning features with business objectives and organizing them by quarter. {other_context}"),
            ("user", "For user feedback, I recommend implementing a structured collection system and integrating insights into our sprint planning. {other_context}"),
            ("feature", "For feature prioritization, we should use a framework that considers business value, user impact, and implementation complexity. {other_context}")
        ]
    },
    "UI/UXDesigner": {
        "domain": "user interface and experience design",
        "conditions": [
            ("design", "For design systems, I recommend creating a component library that ensures consistency across the application. {other_context}"),
            ("user experience", "For improving user experience, we should conduct usability testing and iterate based on user feedback. {other_context}"),
            ("interface", "For interface layouts, I suggest a clean, minimalist approach with clear visual hierarchy and intuitive navigation. {other_context}")
        ]
    },
    "technicalWriter": {
        "domain": "documentation and technical content",
        "conditions": [
            ("document", "For documentation structure, I recommend a tiered approach with quick start guides, detailed references, and tutorials. {other_context}"),
            ("guide", "For user guides, we should focus on task-based instructions with clear examples and visuals. {other_context}"),
            ("api", "For API documentation, I suggest providing clear endpoint descriptions, parameter details, and usage examples. {other_context}")
        ]
    },
    "customerSuccess": {
        "domain": "customer support and satisfaction",
        "conditions": [
            ("onboard", "For customer onboarding, I recommend a structured process with interactive tutorials and regular check-ins. {other_context}"),
            ("support", "For support workflows, we should implement a tiered system with clear escalation paths. {other_context}"),
            ("feedback", "For customer feedback collection, I suggest implementing both passive and active methods at various touchpoints. {other_context}")
        ]
    },
    "marketing&Sales": {
        "domain": "marketing strategy and sales",
        "conditions": [
            ("campaign", "For marketing campaigns, I recommend a multi-channel approach aligned with our target audience personas. {other_context}"),
            ("market", "For market analysis, we should examine competition, trends, and customer needs to identify opportunities. {other_context}"),
            ("sales", "For sales strategies, I suggest focusing on value-based selling that aligns with customer needs. {other_context}")
        ]
    },
    "legalCompliance": {
        "domain": "legal and regulatory compliance",
        "conditions": [
            ("compliance", "For compliance frameworks, I recommend implementing a systematic approach that covers all relevant regulations. {other_context}"),
            ("privacy", "For privacy concerns, we should ensure GDPR and CCPA compliance with transparent data handling policies. {other_context}"),
            ("regulation", "For regulatory updates, I suggest establishing a monitoring system that alerts us to relevant changes. {other_context}")
        ]
    }
}

def main():
    agents_dir = "agents"
    
    # Skip if already updated
    for filename in os.listdir(agents_dir):
        if filename.endswith(".py") and filename not in UPDATED_AGENTS and filename != "__init__.py" and filename != "base_agent.py":
            filepath = os.path.join(agents_dir, filename)
            
            # Read current file
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Extract class name
            class_match = re.search(r'class\s+(\w+)', content)
            if not class_match:
                print(f"Could not find class name in {filename}, skipping.")
                continue
            
            class_name = class_match.group(1)
            
            # Determine role from class name
            role = ' '.join(re.findall('[A-Z][^A-Z]*', class_name))
            
            # Get backstory from content
            backstory_match = re.search(r'backstory\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            backstory = backstory_match.group(1) if backstory_match else "Expert in this domain."
            
            # Get goal from content
            goal_match = re.search(r'goal\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            goal = goal_match.group(1) if goal_match else f"Help with {role} related tasks."
            
            # Get response conditions
            responses = AGENT_RESPONSES.get(role, {
                "domain": "this domain",
                "conditions": [
                    ("implement", f"For implementation strategies in {role}, I recommend focusing on industry best practices. {{other_context}}"),
                    ("best practice", f"When considering best practices for {role}, it's important to balance theory with practical considerations. {{other_context}}"),
                ]
            })
            
            # Format response conditions
            conditions_text = ""
            for keyword, response in responses["conditions"]:
                conditions_text += f"        if \"{keyword}\" in message.lower():\n"
                conditions_text += f"            return f\"{response}\"\n"
            
            # Create updated file content
            updated_content = AGENT_TEMPLATE.format(
                class_name=class_name,
                role=role,
                goal=goal,
                backstory=backstory,
                domain=responses["domain"],
                response_conditions=conditions_text
            )
            
            # Write updated file
            with open(filepath, 'w') as f:
                f.write(updated_content)
            
            print(f"Updated {filename}")

if __name__ == "__main__":
    main()
    print("Agent update completed.") 