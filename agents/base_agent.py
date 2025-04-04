import asyncio
from memory.shared_memory import shared_memory
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from utils.project_manager import ProjectManager
import google.generativeai as genai
from utils.config import get_gemini_config, get_gemini_response

class BaseAgent(ABC, BaseModel):
    """Base class for all agents in the system."""
    
    role: str = Field(..., description="The role of the agent")
    goal: str = Field(..., description="The goal of the agent")
    backstory: str = Field(..., description="The backstory of the agent")
    project_manager: Optional[ProjectManager] = Field(None, description="Project manager instance")
    memory: Any = Field(default=shared_memory, description="Shared memory instance")
    conversations: List[Dict[str, Any]] = Field(default_factory=list, description="List of conversations")
    gemini_config: Dict[str, Any] = Field(default_factory=dict, description="Gemini API configuration")
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "examples": [
                {
                    "role": "Software Engineer",
                    "goal": "Develop high-quality software solutions",
                    "backstory": "Experienced software engineer with expertise in multiple programming languages",
                    "project_manager": None,
                    "memory": None,
                    "conversations": [],
                    "gemini_config": {}
                }
            ]
        }
    }
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize Gemini configuration
        self.gemini_config = get_gemini_config()
    
    @abstractmethod
    def _generate_response(self, message: str, context: Dict[str, Any] = None) -> str:
        """Generate a response based on the input message and context."""
        pass
    
    async def execute(self, task: str):
        """Execute a task."""
        try:
            response = self._generate_response(f"Please execute this task: {task}")
            self.add_conversation("system", f"Task: {task}")
            self.add_conversation("agent", response)
            return response
        except Exception:
            return False
    
    async def chat(self, message: str):
        """Process a chat message and return a response"""
        # Get context for this agent including shared knowledge
        context = self.memory.get_agent_context(self.role)
        
        # Generate a response based on the message and context
        response = self._generate_response(message, context)
        
        # Store the conversation in memory
        self.memory.add_message(self.role, message, response)
        
        return response
    
    def set_project_manager(self, project_manager: ProjectManager):
        """Set the project manager for this agent"""
        self.project_manager = project_manager

    def add_conversation(self, role: str, content: str):
        """Add a conversation entry to the agent's history."""
        self.conversations.append({
            "role": role,
            "content": content
        })
    
    def get_conversations(self) -> List[Dict[str, Any]]:
        """Get the agent's conversation history."""
        return self.conversations
    
    def clear_conversations(self):
        """Clear the agent's conversation history."""
        self.conversations = []
    
    # File operations methods (can be used by any agent)
    def create_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Create a file in the project."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.create_file(project_name, file_path, content)
    
    def read_file(self, project_name: str, file_path: str) -> str:
        """Read a file from the project."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.read_file(project_name, file_path)
    
    def update_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Update a file in the project."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.update_file(project_name, file_path, content)
    
    def list_files(self, project_name: str, directory: str = "") -> List[str]:
        """List files in a project directory."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.list_files(project_name, directory)
    
    # Task management methods
    def add_task(self, project_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Add a task to the project."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.add_task(project_name, task)
    
    def update_task_status(self, project_name: str, task_id: str, status: str) -> Dict[str, Any]:
        """Update a task's status."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.update_task_status(project_name, task_id, status)
    
    def get_tasks(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all tasks in a project."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.get_tasks(project_name)
    
    # Project management methods
    def create_project(self, name: str, description: str) -> Dict[str, Any]:
        """Create a new project."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.create_project(name, description)
    
    def get_project(self, name: str) -> Dict[str, Any]:
        """Get project details."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.get_project(name)
    
    def plan_project(self, project_name: str) -> Dict[str, Any]:
        """Create a project plan with tasks."""
        if not self.project_manager:
            raise ValueError("Project manager not set")
        return self.project_manager.plan_project(project_name)

    def get_my_tasks(self) -> list:
        """Get tasks assigned to this agent"""
        if not self.project_manager:
            return []
        return [
            task for task in self.project_manager.get_tasks(self.project_manager.current_project)
            if task.get("assigned_to") == self.role
        ] 