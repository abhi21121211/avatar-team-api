import asyncio
from memory.mongo_memory import mongo_shared_memory
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from utils.project_manager import ProjectManager
import google.generativeai as genai
from utils.config import get_gemini_config, get_gemini_response

# Import function to get team member names
try:
    from utils.database import get_team_member_name
except ImportError:
    # Mock function for compatibility if database module doesn't have it
    async def get_team_member_name(role):
        return None

class BaseAgent(ABC, BaseModel):
    """Base class for all agents in the system."""
    
    role: str = Field(..., description="The role of the agent")
    goal: str = Field(..., description="The goal of the agent")
    backstory: str = Field(..., description="The backstory of the agent")
    project_manager: Optional[ProjectManager] = Field(None, description="Project manager instance")
    memory: Any = Field(default=mongo_shared_memory, description="Shared memory instance")
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
    
    # Add a method to prepare context with name awareness
    def _prepare_name_aware_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Prepare the message with name awareness instructions when the user asks
        about the agent's name or identity.
        """
        display_name = context.get("display_name", "")
        
        # Check if the message is asking about the agent's name or identity
        name_queries = [
            "what is your name", 
            "who are you", 
            "your name", 
            "introduce yourself",
            "tell me about yourself",
            "what should i call you"
        ]
        
        is_name_query = any(query in message.lower() for query in name_queries)
        
        if is_name_query and display_name:
            # Add specific instructions for name-related queries
            return f"""When responding to this message, remember that your name is "{display_name}".
If asked about your name or identity, clearly state that your name is "{display_name}".

User message: {message}"""
        
        return message
        
    async def get_display_name(self) -> str:
        """Get the display name for this agent, using custom name if available"""
        try:
            custom_name = await get_team_member_name(self.role)
            if custom_name and "name" in custom_name:
                return custom_name["name"]
            else:
                # Format the role name if no custom name
                import re
                parts = re.findall(r'[A-Z][a-z]*', self.role)
                return " ".join(parts).title() if parts else self.role.title()
        except Exception as e:
            print(f"Error getting agent display name: {str(e)}")
            # Format the role name if error
            import re
            parts = re.findall(r'[A-Z][a-z]*', self.role)
            return " ".join(parts).title() if parts else self.role.title()
    
    async def execute(self, task: str):
        """Execute a task."""
        try:
            # Get context for this agent including shared knowledge
            context = await self.memory.get_agent_context(self.role)
            
            # Get agent's display name
            display_name = await self.get_display_name()
            
            # Add display name to context
            if context is None:
                context = {}
            context["display_name"] = display_name
            
            # Prepare name-aware message
            name_aware_task = self._prepare_name_aware_message(f"Please execute this task: {task}", context)
            
            response = self._generate_response(name_aware_task, context)
            self.add_conversation("system", f"Task: {task}")
            self.add_conversation("agent", response)
            return response
        except Exception as e:
            print(f"Error executing task: {str(e)}")
            return f"Error: {str(e)}"
    
    async def chat(self, message: str):
        """Process a chat message and return a response"""
        try:
            # Get context for this agent including shared knowledge
            context = await self.memory.get_agent_context(self.role)
            
            # Get agent's display name
            display_name = await self.get_display_name()
            
            # Add display name to context
            if context is None:
                context = {}
            context["display_name"] = display_name
            
            # Prepare name-aware message
            name_aware_message = self._prepare_name_aware_message(message, context)
            
            # Generate a response based on the message and context
            response = self._generate_response(name_aware_message, context)
            
            # Store the conversation in memory
            await self.memory.add_message(self.role, message, response)
            
            return response
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            # If there's an error getting context, try to generate a response without it
            try:
                # Still try to get the display name
                try:
                    display_name = await self.get_display_name()
                    context = {"display_name": display_name}
                    
                    # Prepare name-aware message even in error case
                    name_aware_message = self._prepare_name_aware_message(message, context)
                    
                    response = self._generate_response(name_aware_message, context)
                except:
                    context = {}
                    response = self._generate_response(message, context)
                    
                self.add_conversation("user", message)
                self.add_conversation("agent", response)
                return response
            except Exception as inner_e:
                print(f"Failed to generate response: {str(inner_e)}")
                return f"I'm having trouble processing your request due to a system error: {str(e)}"
    
    def set_project_manager(self, project_manager: ProjectManager):
        """Set the project manager for this agent"""
        self.project_manager = project_manager

    def add_conversation(self, role: str, content: str):
        """Add a conversation entry to the agent's history."""
        self.conversations.append({
            "role": role,
            "content": content,
            "project": self.project_manager.current_project if self.project_manager else ""
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