from agents.base_agent import BaseAgent
from utils.config import get_gemini_response
from utils.project_manager import ProjectManager
import os
import uuid
from typing import Dict, Any, List
import google.generativeai as genai

class ChiefArchitect(BaseAgent):
    """Chief Architect agent responsible for high-level system design and architecture."""
    
    def __init__(self, **data):
        data.update({
            "role": "chiefArchitect",
            "goal": "Design and oversee the implementation of robust, scalable, and maintainable software architectures",
            "backstory": """You are an experienced Chief Architect with expertise in designing complex software systems.
            You excel at creating scalable architectures, making technical decisions, and ensuring system quality.
            Your role is to guide the technical direction of projects and ensure architectural consistency."""
        })
        super().__init__(**data)
        if not self.project_manager:
            self.project_manager = ProjectManager("projects")
    
    def _generate_response(self, message: str, context: Dict = None) -> str:
        """Generate a response based on the input message."""
        # Get relevant context from other agents
        other_context = ""
        if context and "all_conversations" in context:
            for agent, convos in context["all_conversations"].items():
                if agent != self.role and convos:
                    latest = convos[-1]
                    other_context += f"{agent} discussed: {latest['user_message']} → {latest['agent_response']}\n"
        
        # Check if the message is about project management
        if "create project" in message.lower() or "new project" in message.lower():
            return self._handle_project_creation(message)
        elif "plan" in message.lower() or "architecture" in message.lower():
            return self._handle_project_planning(message)
        elif "assign" in message.lower() or "task" in message.lower():
            return self._handle_task_assignment(message)
            
        # Generate response using Gemini
        prompt = f"""As the Chief Architect, respond to the following message:
        {message}
        
        Relevant context from other agents:
        {other_context}
        
        Provide a professional and technical response focusing on architecture, system design, and technical decisions."""
        
        return get_gemini_response(prompt)
    
    def _handle_project_creation(self, message):
        """Handle project creation request"""
        try:
            # Extract project details from message
            prompt = f"""Extract project name and description from this message: {message}
            Return in format: {{"name": "project_name", "description": "project_description"}}"""
            
            project_info = get_gemini_response(prompt)
            project_info = eval(project_info)  # Convert string to dict
            
            # Create project
            project = self.project_manager.create_project(
                project_info["name"],
                project_info["description"]
            )
            
            return f"""Project '{project_info['name']}' has been created successfully!
            Project structure has been initialized with standard directories.
            Would you like me to help you plan the project architecture and assign tasks to team members?"""
            
        except Exception as e:
            return f"Error creating project: {str(e)}"

    def _handle_project_planning(self, message):
        """Handle project planning request"""
        if not self.project_manager or not self.project_manager.current_project:
            return "Please create a project first before planning."
        
        try:
            # Plan the project
            project = self.project_manager.plan_project(self.project_manager.current_project)
            
            return f"""Project plan has been created successfully!
            - {len(project["tasks"])} tasks have been added
            - Standard architecture has been defined
            Would you like me to explain the architecture or make any modifications?"""
            
        except Exception as e:
            return f"Error planning project: {str(e)}"

    def _handle_task_assignment(self, message):
        """Handle task assignment request"""
        if not self.project_manager or not self.project_manager.current_project:
            return "Please create a project first before assigning tasks."
        
        try:
            # Get current tasks
            tasks = self.project_manager.get_tasks(self.project_manager.current_project)
            
            # Create a response about task assignments
            task_list = "\n".join([f"- {t['name']} (assigned to {t['assigned_to']})" for t in tasks])
            
            return f"""Here are the current task assignments:
            
            {task_list}
            
            Would you like me to update any of these assignments?"""
            
        except Exception as e:
            return f"Error retrieving tasks: {str(e)}"

    def create_project(self, project_name: str, description: str) -> Dict[str, Any]:
        """Create a new project with the given name and description."""
        return self.project_manager.create_project(project_name, description)
    
    def plan_project(self, project_name: str) -> Dict[str, Any]:
        """Create a project plan with tasks and milestones."""
        return self.project_manager.plan_project(project_name)
    
    def assign_task(self, project_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assign a task to a team member."""
        return self.project_manager.add_task(project_name, task)
