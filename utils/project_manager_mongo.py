import os
import json
import uuid
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from utils.database import (
    create_project as db_create_project,
    get_project as db_get_project,
    list_projects as db_list_projects,
    add_task as db_add_task,
    update_task_status as db_update_task_status,
    create_or_update_file as db_create_or_update_file,
    get_file as db_get_file,
    plan_project as db_plan_project
)

class MongoProjectManager:
    """Manages project configurations, files, and tasks using MongoDB."""
    
    def __init__(self, base_directory: str):
        # We'll still keep the base directory for storing physical files
        self.base_directory = base_directory
        self._ensure_base_directory()
        self.current_project = None
    
    def _ensure_base_directory(self):
        """Ensure the base directory exists."""
        if not os.path.exists(self.base_directory):
            os.makedirs(self.base_directory)
    
    async def create_project(self, name: str, description: str) -> Dict[str, Any]:
        """Create a new project with the specified name and description."""
        project_dir = os.path.join(self.base_directory, name)
        
        # Create project directory if it doesn't exist
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
            
        # Create source code directory
        src_dir = os.path.join(project_dir, "src")
        if not os.path.exists(src_dir):
            os.makedirs(src_dir)
        
        # Create documentation directory
        docs_dir = os.path.join(project_dir, "docs")
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)
        
        # Create project in MongoDB
        project = await db_create_project(name, description)
        
        # Create README.md
        readme_path = os.path.join(project_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"# {name}\n\n{description}\n\n## Getting Started\n\nThis project is managed by the AI Avatar Team.")
        
        # Store README in MongoDB
        await db_create_or_update_file(name, "README.md", f"# {name}\n\n{description}\n\n## Getting Started\n\nThis project is managed by the AI Avatar Team.")
        
        self.current_project = name
        return project.dict()
    
    async def get_project(self, name: str) -> Dict[str, Any]:
        """Get project configuration by name."""
        project = await db_get_project(name)
        if not project:
            raise FileNotFoundError(f"Project {name} does not exist")
        return project.dict()
    
    async def list_projects(self) -> List[str]:
        """List all available projects."""
        projects = await db_list_projects()
        return [project.name for project in projects]
    
    async def create_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Create a new file in the project."""
        project_dir = os.path.join(self.base_directory, project_name)
        full_path = os.path.join(project_dir, file_path)
        
        # Create directories in the path if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write content to the file
        with open(full_path, "w") as f:
            f.write(content)
        
        # Store in MongoDB
        file = await db_create_or_update_file(project_name, file_path, content)
        
        return file.dict()
    
    async def read_file(self, project_name: str, file_path: str) -> str:
        """Read a file from the project."""
        # Try to get from MongoDB first
        content = await db_get_file(project_name, file_path)
        
        if content is None:
            # Fallback to file system
            project_dir = os.path.join(self.base_directory, project_name)
            full_path = os.path.join(project_dir, file_path)
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"File {file_path} does not exist in project {project_name}")
            
            with open(full_path, "r") as f:
                content = f.read()
                
            # Store in MongoDB for future access
            await db_create_or_update_file(project_name, file_path, content)
        
        return content
    
    async def update_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Update a file in the project."""
        project_dir = os.path.join(self.base_directory, project_name)
        full_path = os.path.join(project_dir, file_path)
        
        # Create directories in the path if they don't exist (for new files)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write content to the file
        with open(full_path, "w") as f:
            f.write(content)
        
        # Update in MongoDB
        file = await db_create_or_update_file(project_name, file_path, content)
        
        return file.dict()
    
    async def list_files(self, project_name: str, directory: str = "") -> List[str]:
        """List files in a project directory."""
        project_dir = os.path.join(self.base_directory, project_name)
        target_dir = os.path.join(project_dir, directory)
        
        if not os.path.exists(target_dir):
            raise FileNotFoundError(f"Directory {directory} does not exist in project {project_name}")
        
        files = []
        for root, dirs, filenames in os.walk(target_dir):
            rel_path = os.path.relpath(root, project_dir)
            if rel_path == ".":
                rel_path = ""
            
            for filename in filenames:
                file_path = os.path.join(rel_path, filename)
                files.append(file_path)
        
        return files
    
    async def add_task(self, project_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Add a task to the project."""
        task_id = task.get("id", str(uuid.uuid4()))
        task_data = {
            "id": task_id,
            "name": task.get("name", "Unnamed Task"),
            "description": task.get("description", ""),
            "assigned_to": task.get("assigned_to", ""),
            "status": task.get("status", "pending"),
        }
        
        task_obj = await db_add_task(project_name, task_data)
        
        return task_obj.dict()
    
    async def update_task_status(self, project_name: str, task_id: str, status: str) -> Dict[str, Any]:
        """Update a task's status."""
        task = await db_update_task_status(project_name, task_id, status)
        
        if not task:
            raise ValueError(f"Task {task_id} not found in project {project_name}")
        
        return task.dict()
    
    async def get_tasks(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all tasks in a project."""
        project = await db_get_project(project_name)
        if not project:
            raise FileNotFoundError(f"Project {project_name} not found")
        
        return [task.dict() for task in project.tasks]
    
    def _run_async_in_sync_context(self, coro):
        """Helper method to run async code in a synchronous context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(coro)
                return loop.run_until_complete(task)
            else:
                return asyncio.run(coro)
        except RuntimeError:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
    
    def create_project_sync(self, name: str, description: str) -> Dict[str, Any]:
        """Synchronous wrapper for create_project."""
        return self._run_async_in_sync_context(self.create_project(name, description))
    
    def get_project_sync(self, name: str) -> Dict[str, Any]:
        """Synchronous wrapper for get_project."""
        return self._run_async_in_sync_context(self.get_project(name))
    
    def list_projects_sync(self) -> List[str]:
        """Synchronous wrapper for list_projects."""
        return self._run_async_in_sync_context(self.list_projects())
    
    def create_file_sync(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Synchronous wrapper for create_file."""
        return self._run_async_in_sync_context(self.create_file(project_name, file_path, content))
    
    def read_file_sync(self, project_name: str, file_path: str) -> str:
        """Synchronous wrapper for read_file."""
        return self._run_async_in_sync_context(self.read_file(project_name, file_path))
    
    def update_file_sync(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Synchronous wrapper for update_file."""
        return self._run_async_in_sync_context(self.update_file(project_name, file_path, content))
    
    def list_files_sync(self, project_name: str, directory: str = "") -> List[str]:
        """Synchronous wrapper for list_files."""
        return self._run_async_in_sync_context(self.list_files(project_name, directory))
    
    def add_task_sync(self, project_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for add_task."""
        return self._run_async_in_sync_context(self.add_task(project_name, task))
    
    def update_task_status_sync(self, project_name: str, task_id: str, status: str) -> Dict[str, Any]:
        """Synchronous wrapper for update_task_status."""
        return self._run_async_in_sync_context(self.update_task_status(project_name, task_id, status))
    
    def get_tasks_sync(self, project_name: str) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_tasks."""
        return self._run_async_in_sync_context(self.get_tasks(project_name))
    
    def plan_project_sync(self, project_name: str) -> Dict[str, Any]:
        """Synchronous wrapper for plan_project."""
        try:
            # Create a new event loop to avoid conflicts
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(db_plan_project(project_name))
                return result
            finally:
                new_loop.close()
                asyncio.set_event_loop(None)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in plan_project_sync: {str(e)}\n{error_details}")
            raise
    
    # For compatibility with the original implementation
    def create_project(self, name: str, description: str) -> Dict[str, Any]:
        return self.create_project_sync(name, description)
    
    def get_project(self, name: str) -> Dict[str, Any]:
        # Direct access to db_get_project to avoid recursion
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._run_async_in_sync_context(db_get_project(name)).dict()
            else:
                result = asyncio.run(db_get_project(name))
                return result.dict() if result else {}
        except RuntimeError:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(db_get_project(name))
                return result.dict() if result else {}
            finally:
                new_loop.close()
    
    def list_projects(self) -> List[str]:
        return self.list_projects_sync()
    
    def create_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        return self.create_file_sync(project_name, file_path, content)
    
    def read_file(self, project_name: str, file_path: str) -> str:
        return self.read_file_sync(project_name, file_path)
    
    def update_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        return self.update_file_sync(project_name, file_path, content)
    
    def list_files(self, project_name: str, directory: str = "") -> List[str]:
        return self.list_files_sync(project_name, directory)
    
    def add_task(self, project_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        return self.add_task_sync(project_name, task)
    
    def update_task_status(self, project_name: str, task_id: str, status: str) -> Dict[str, Any]:
        return self.update_task_status_sync(project_name, task_id, status)
    
    def get_tasks(self, project_name: str) -> List[Dict[str, Any]]:
        return self.get_tasks_sync(project_name)
    
    def plan_project(self, project_name: str) -> Dict[str, Any]:
        """Create a project plan with tasks for team members."""
        return self.plan_project_sync(project_name)
    
    def import_existing_project(self, source_dir: str, project_name: str, description: str) -> Dict[str, Any]:
        """Import an existing project from a directory.""" 