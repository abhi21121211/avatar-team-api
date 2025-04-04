import os
import json
import uuid
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime

class ProjectManager:
    """Manages project configurations, files, and tasks."""
    
    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        self._ensure_base_directory()
        self.current_project = None
    
    def _ensure_base_directory(self):
        """Ensure the base directory exists."""
        if not os.path.exists(self.base_directory):
            os.makedirs(self.base_directory)
    
    def create_project(self, name: str, description: str) -> Dict[str, Any]:
        """Create a new project with the specified name and description."""
        project_id = str(uuid.uuid4())
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
        
        # Create project config file
        project_config = {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tasks": [],
            "files": [],
            "structure": {
                "src": {"type": "directory", "children": {}},
                "docs": {"type": "directory", "children": {}}
            }
        }
        
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(project_config, f, indent=2)
        
        # Create README.md
        readme_path = os.path.join(project_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"# {name}\n\n{description}\n\n## Getting Started\n\nThis project is managed by the AI Avatar Team.")
        
        self.current_project = name
        return project_config
    
    def get_project(self, name: str) -> Dict[str, Any]:
        """Get project configuration by name."""
        project_dir = os.path.join(self.base_directory, name)
        config_file = os.path.join(project_dir, "project_config.json")
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Project {name} does not exist")
        
        with open(config_file, "r") as f:
            return json.load(f)
    
    def list_projects(self) -> List[str]:
        """List all available projects."""
        if not os.path.exists(self.base_directory):
            return []
        
        return [d for d in os.listdir(self.base_directory) 
                if os.path.isdir(os.path.join(self.base_directory, d))]
    
    def create_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Create a new file in the project."""
        project_dir = os.path.join(self.base_directory, project_name)
        full_path = os.path.join(project_dir, file_path)
        
        # Create directories in the path if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write content to the file
        with open(full_path, "w") as f:
            f.write(content)
        
        # Update project config
        config = self.get_project(project_name)
        file_info = {
            "id": str(uuid.uuid4()),
            "path": file_path,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        config["files"].append(file_info)
        
        # Update structure
        parts = file_path.split(os.sep)
        current = config["structure"]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:  # Last part (file)
                current.setdefault(part, {"type": "file"})
            else:  # Directory
                if part not in current:
                    current[part] = {"type": "directory", "children": {}}
                current = current[part]["children"]
        
        # Save updated config
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        return file_info
    
    def read_file(self, project_name: str, file_path: str) -> str:
        """Read a file from the project."""
        project_dir = os.path.join(self.base_directory, project_name)
        full_path = os.path.join(project_dir, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {file_path} does not exist in project {project_name}")
        
        with open(full_path, "r") as f:
            return f.read()
    
    def update_file(self, project_name: str, file_path: str, content: str) -> Dict[str, Any]:
        """Update a file in the project."""
        project_dir = os.path.join(self.base_directory, project_name)
        full_path = os.path.join(project_dir, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {file_path} does not exist in project {project_name}")
        
        # Write content to the file
        with open(full_path, "w") as f:
            f.write(content)
        
        # Update project config
        config = self.get_project(project_name)
        file_info = None
        for file in config["files"]:
            if file["path"] == file_path:
                file["updated_at"] = datetime.now().isoformat()
                file_info = file
                break
        
        if not file_info:
            file_info = {
                "id": str(uuid.uuid4()),
                "path": file_path,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            config["files"].append(file_info)
        
        # Save updated config
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        return file_info
    
    def delete_file(self, project_name: str, file_path: str) -> bool:
        """Delete a file from the project."""
        project_dir = os.path.join(self.base_directory, project_name)
        full_path = os.path.join(project_dir, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {file_path} does not exist in project {project_name}")
        
        # Delete the file
        os.remove(full_path)
        
        # Update project config
        config = self.get_project(project_name)
        config["files"] = [f for f in config["files"] if f["path"] != file_path]
        
        # Remove from structure
        parts = file_path.split(os.sep)
        current = config["structure"]
        for i, part in enumerate(parts[:-1]):
            if part in current:
                current = current[part]["children"]
            else:
                break
        
        if parts[-1] in current:
            del current[parts[-1]]
        
        # Save updated config
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        return True
    
    def list_files(self, project_name: str, directory: str = "") -> List[str]:
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
                if filename != "project_config.json":
                    file_path = os.path.join(rel_path, filename)
                    files.append(file_path)
        
        return files
    
    def add_task(self, project_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Add a task to the project."""
        config = self.get_project(project_name)
        
        task_id = task.get("id", str(uuid.uuid4()))
        new_task = {
            "id": task_id,
            "name": task.get("name", "Unnamed Task"),
            "description": task.get("description", ""),
            "assigned_to": task.get("assigned_to", ""),
            "status": task.get("status", "pending"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        config["tasks"].append(new_task)
        
        # Save updated config
        project_dir = os.path.join(self.base_directory, project_name)
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        return new_task
    
    def update_task_status(self, project_name: str, task_id: str, status: str) -> Dict[str, Any]:
        """Update a task's status."""
        config = self.get_project(project_name)
        
        task = None
        for t in config["tasks"]:
            if t["id"] == task_id:
                t["status"] = status
                t["updated_at"] = datetime.now().isoformat()
                task = t
                break
        
        if not task:
            raise ValueError(f"Task {task_id} not found in project {project_name}")
        
        # Save updated config
        project_dir = os.path.join(self.base_directory, project_name)
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        return task
    
    def get_tasks(self, project_name: str) -> List[Dict[str, Any]]:
        """Get all tasks in a project."""
        config = self.get_project(project_name)
        return config["tasks"]
    
    def get_task(self, project_name: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        config = self.get_project(project_name)
        
        for task in config["tasks"]:
            if task["id"] == task_id:
                return task
        
        return None
    
    def plan_project(self, project_name: str) -> Dict[str, Any]:
        """Create a project plan with tasks for team members."""
        # Create standard tasks for each team role
        tasks = [
            {
                "id": str(uuid.uuid4()),
                "name": "Design system architecture",
                "description": "Create a detailed system design and architecture diagram",
                "assigned_to": "chiefArchitect",
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Set up project structure",
                "description": "Initialize the basic project structure and files",
                "assigned_to": "backendEngineer",
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Create UI mockups",
                "description": "Design the user interface components and layouts",
                "assigned_to": "uiUxDesigner",
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Implement frontend components",
                "description": "Develop the React/Next.js components for the UI",
                "assigned_to": "frontendEngineer",
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Implement backend APIs",
                "description": "Develop the API endpoints and database models",
                "assigned_to": "backendEngineer",
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Set up CI/CD pipeline",
                "description": "Configure continuous integration and deployment",
                "assigned_to": "devopsEngineer",
                "status": "pending"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Document API endpoints",
                "description": "Create comprehensive API documentation",
                "assigned_to": "technicalWriter",
                "status": "pending"
            }
        ]
        
        # Add tasks to project
        config = self.get_project(project_name)
        for task in tasks:
            config["tasks"].append({
                "id": task["id"],
                "name": task["name"],
                "description": task["description"],
                "assigned_to": task["assigned_to"],
                "status": task["status"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            })
        
        # Save updated config
        project_dir = os.path.join(self.base_directory, project_name)
        config_file = os.path.join(project_dir, "project_config.json")
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        
        return config
    
    def import_existing_project(self, source_dir: str, project_name: str, description: str) -> Dict[str, Any]:
        """Import an existing project directory into the manager."""
        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"Source directory {source_dir} does not exist")
        
        # Create project config
        project_config = self.create_project(project_name, description)
        
        # Copy files from source directory
        project_dir = os.path.join(self.base_directory, project_name)
        
        # Track imported files for reporting
        imported_files = []
        skipped_files = []
        
        # Define binary file extensions that should be directly copied without reading
        binary_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.mp3', '.mp4', '.wav', '.avi', '.mov', '.mkv',
            '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
            '.exe', '.dll', '.so', '.dylib',
            '.pyc', '.pyd', '.pyo',
            '.jar', '.war', '.ear',
            '.db', '.sqlite', '.sqlite3',
            '.xls', '.xlsx', '.doc', '.docx', '.ppt', '.pptx'
        }
        
        # Skip these directories
        skip_dirs = {'.git', '.svn', 'node_modules', '__pycache__', 'venv', 'env', '.env', '.venv', '.vs', '.idea'}
        
        try:
            # For each file in the source directory, copy it to the project
            for root, dirs, files in os.walk(source_dir):
                # Skip directories that should be excluded
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                
                for file in files:
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, source_dir)
                    dest_path = os.path.join(project_dir, rel_path)
                    
                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Check file size to avoid attempting to read very large files
                    file_size = os.path.getsize(src_path)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    # Handle the file based on type and size
                    try:
                        if file_ext in binary_extensions or file_size > 10 * 1024 * 1024:  # 10MB limit for reading
                            # Just copy the file without reading it
                            shutil.copy2(src_path, dest_path)
                            
                            # Add file to project config without content
                            file_info = {
                                "id": str(uuid.uuid4()),
                                "path": rel_path,
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat(),
                                "binary": True
                            }
                            project_config["files"].append(file_info)
                            imported_files.append(rel_path)
                        else:
                            # Try to read as text and update the project config
                            try:
                                with open(src_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                
                                # Write content to the destination
                                with open(dest_path, "w", encoding="utf-8") as f:
                                    f.write(content)
                                
                                # Add file to project config
                                file_info = {
                                    "id": str(uuid.uuid4()),
                                    "path": rel_path,
                                    "created_at": datetime.now().isoformat(),
                                    "updated_at": datetime.now().isoformat(),
                                    "binary": False
                                }
                                project_config["files"].append(file_info)
                                imported_files.append(rel_path)
                            except UnicodeDecodeError:
                                # If we can't read as text, it's probably binary
                                shutil.copy2(src_path, dest_path)
                                file_info = {
                                    "id": str(uuid.uuid4()),
                                    "path": rel_path,
                                    "created_at": datetime.now().isoformat(),
                                    "updated_at": datetime.now().isoformat(),
                                    "binary": True
                                }
                                project_config["files"].append(file_info)
                                imported_files.append(rel_path)
                    except Exception as e:
                        print(f"Error importing file {rel_path}: {str(e)}")
                        skipped_files.append(rel_path)
            
            # Update project config with import info
            project_config["import_info"] = {
                "source_directory": source_dir,
                "imported_at": datetime.now().isoformat(),
                "file_count": len(imported_files),
                "skipped_count": len(skipped_files)
            }
            
            # Save updated config
            config_file = os.path.join(project_dir, "project_config.json")
            with open(config_file, "w") as f:
                json.dump(project_config, f, indent=2)
            
            # Set as current project
            self.current_project = project_name
            
            return project_config
        except Exception as e:
            # If import fails, attempt to clean up
            try:
                if os.path.exists(project_dir):
                    shutil.rmtree(project_dir)
            except:
                pass
            
            # Re-raise the exception
            raise Exception(f"Failed to import project: {str(e)}") 