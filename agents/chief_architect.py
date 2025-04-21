from agents.base_agent import BaseAgent
from utils.config import get_gemini_response
from utils.project_manager import ProjectManager
import os
import uuid
from typing import Dict, Any, List
import google.generativeai as genai
import requests

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
            
            # Import needed modules
            import concurrent.futures
            import asyncio
            import motor.motor_asyncio
            import os
            from dotenv import load_dotenv
            from datetime import datetime
            
            project_name = project_info["name"]
            project_description = project_info["description"]
            
            # Define the project creation function with proper error handling
            def run_async_func():
                # Set up a thread-local event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Load environment variables
                load_dotenv()
                
                # MongoDB Configuration with error handling
                MONGODB_URI = os.getenv("MONGODB_URI")
                if not MONGODB_URI:
                    return {"error": "MONGODB_URI environment variable is not set"}
                
                # Create a new client with proper connection timeout and retry options
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                
                # Function to run with the new client
                async def run_with_new_client():
                    try:
                        # Check if we can connect to the database
                        try:
                            # Ping the MongoDB server to check connection
                            await client.admin.command('ping')
                        except Exception as e:
                            return {"error": f"Failed to connect to MongoDB: {str(e)}"}
                        
                        db = client.avatar_team_db
                        
                        # Check if project already exists
                        try:
                            existing = await db.projects.find_one({"name": project_name})
                            if existing:
                                return {"error": f"Project {project_name} already exists"}
                        except Exception as e:
                            return {"error": f"Failed to check if project exists: {str(e)}"}
                        
                        # Create project in MongoDB
                        project_data = {
                            "name": project_name,
                            "description": project_description,
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                            "tasks": []
                        }
                        
                        try:
                            await db.projects.insert_one(project_data)
                        except Exception as e:
                            return {"error": f"Failed to create project in database: {str(e)}"}
                        
                        # Create project directory if needed
                        if self.project_manager:
                            try:
                                base_directory = self.project_manager.base_directory
                                project_dir = os.path.join(base_directory, project_name)
                                
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
                                    
                                # Create README.md
                                readme_content = f"# {project_name}\n\n{project_description}\n\n## Getting Started\n\nThis project is managed by the AI Avatar Team."
                                readme_path = os.path.join(project_dir, "README.md")
                                with open(readme_path, "w") as f:
                                    f.write(readme_content)
                            except Exception as e:
                                return {"error": f"Failed to create project directories: {str(e)}"}
                            
                            # Store README in MongoDB
                            try:
                                await db.files.insert_one({
                                    "project_name": project_name,
                                    "file_path": "README.md",
                                    "content": readme_content,
                                    "created_at": datetime.now(),
                                    "updated_at": datetime.now()
                                })
                            except Exception as e:
                                # Non-critical error - project was created but README wasn't stored in DB
                                print(f"Warning: Failed to store README in database: {str(e)}")
                        
                        return {
                            "status": "success",
                            "project": {
                                "name": project_name,
                                "description": project_description
                            }
                        }
                    
                    except Exception as e:
                        return {"error": f"Unexpected error: {str(e)}"}
                    finally:
                        # Always close the client
                        client.close()
                
                try:
                    return loop.run_until_complete(run_with_new_client())
                except Exception as e:
                    return {"error": f"Event loop error: {str(e)}"}
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            # Execute in a separate thread with proper timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    result = executor.submit(run_async_func).result(timeout=30)
                except concurrent.futures.TimeoutError:
                    return "Error creating project: Operation timed out after 30 seconds"
                except Exception as e:
                    return f"Error in thread execution: {str(e)}"
            
            # Check for errors
            if isinstance(result, dict) and "error" in result:
                return f"Error creating project: {result['error']}"
                
            # Store the current project in the project manager for reference
            self.project_manager.current_project = project_name
            
            return f"""Project '{project_name}' has been created successfully!
            Project structure has been initialized with standard directories.
            Would you like me to help you plan the project architecture and assign tasks to team members?"""
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating project: {str(e)}\n{error_details}")
            return f"Error creating project: {str(e)}"

    def _handle_project_planning(self, message):
        """Handle project planning request"""
        if not self.project_manager or not self.project_manager.current_project:
            return "Please create a project first before planning."
        
        try:
            project_name = self.project_manager.current_project
            
            # Import needed modules
            import concurrent.futures
            import asyncio
            import motor.motor_asyncio
            import os
            from dotenv import load_dotenv
            from datetime import datetime
            import uuid
            
            # Define the task creation function with proper error handling
            def run_async_func():
                # Set up a thread-local event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Load environment variables
                load_dotenv()
                
                # MongoDB Configuration with error handling
                MONGODB_URI = os.getenv("MONGODB_URI")
                if not MONGODB_URI:
                    return {"error": "MONGODB_URI environment variable is not set"}
                
                # Create a new client with proper connection timeout and retry options
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                
                # Function to run with the new client
                async def run_with_new_client():
                    try:
                        # Check if we can connect to the database
                        try:
                            # Ping the MongoDB server to check connection
                            await client.admin.command('ping')
                        except Exception as e:
                            return {"error": f"Failed to connect to MongoDB: {str(e)}"}
                        
                        db = client.avatar_team_db
                        
                        # Check if project exists
                        project = await db.projects.find_one({"name": project_name})
                        if not project:
                            return {"error": f"Project {project_name} not found"}
                        
                        # Create standard tasks
                        tasks = [
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Design system architecture",
                                "description": "Create a detailed system design and architecture diagram",
                                "assigned_to": "chiefArchitect",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Set up project structure",
                                "description": "Initialize the basic project structure and files",
                                "assigned_to": "backendEngineer",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Create UI mockups",
                                "description": "Design the user interface components and layouts",
                                "assigned_to": "uiUxDesigner",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Implement frontend components",
                                "description": "Develop the React/Next.js components for the UI",
                                "assigned_to": "frontendEngineer",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Implement backend APIs",
                                "description": "Develop the API endpoints and database models",
                                "assigned_to": "backendEngineer",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Set up CI/CD pipeline",
                                "description": "Configure continuous integration and deployment",
                                "assigned_to": "devopsEngineer",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            },
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Document API endpoints",
                                "description": "Create comprehensive API documentation",
                                "assigned_to": "technicalWriter",
                                "status": "todo",
                                "project_name": project_name,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            }
                        ]
                        
                        # Insert tasks into MongoDB with error handling
                        for task in tasks:
                            try:
                                await db.tasks.insert_one(task)
                            except Exception as e:
                                return {"error": f"Failed to insert task: {str(e)}"}
                        
                        # Update project with has_plan flag
                        try:
                            await db.projects.update_one(
                                {"name": project_name},
                                {"$set": {"has_plan": True, "updated_at": datetime.now()}}
                            )
                        except Exception as e:
                            return {"error": f"Failed to update project: {str(e)}"}
                        
                        return {
                            "status": "success",
                            "project_name": project_name,
                            "task_count": len(tasks)
                        }
                    
                    except Exception as e:
                        return {"error": f"Unexpected error: {str(e)}"}
                    finally:
                        # Always close the client
                        client.close()
                
                try:
                    return loop.run_until_complete(run_with_new_client())
                except Exception as e:
                    return {"error": f"Event loop error: {str(e)}"}
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            # Execute in a separate thread with proper timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    result = executor.submit(run_async_func).result(timeout=30)
                except concurrent.futures.TimeoutError:
                    return "Error planning project: Operation timed out after 30 seconds"
                except Exception as e:
                    return f"Error in thread execution: {str(e)}"
            
            # Check for errors
            if isinstance(result, dict) and "error" in result:
                return f"Error planning project: {result['error']}"
            
            # Success!
            return f"""Project plan has been created successfully!
            - Added {result.get('task_count', 7)} standard tasks to the project
            - Standard architecture has been defined
            
            Would you like me to explain the architecture or make any modifications?"""
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error planning project: {str(e)}\n{error_details}")
            return f"Error planning project: {str(e)}"

    def _handle_task_assignment(self, message):
        """Handle task assignment request"""
        if not self.project_manager or not self.project_manager.current_project:
            return "Please create a project first before assigning tasks."
        
        try:
            project_name = self.project_manager.current_project
            
            # Import needed modules
            import concurrent.futures
            import asyncio
            import motor.motor_asyncio
            import os
            from dotenv import load_dotenv
            
            # Define the task retrieval function with proper error handling
            def run_async_func():
                # Set up a thread-local event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Load environment variables
                load_dotenv()
                
                # MongoDB Configuration with error handling
                MONGODB_URI = os.getenv("MONGODB_URI")
                if not MONGODB_URI:
                    return {"error": "MONGODB_URI environment variable is not set"}
                
                # Create a new client with proper connection timeout and retry options
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    MONGODB_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000
                )
                
                # Function to run with the new client
                async def run_with_new_client():
                    try:
                        # Check if we can connect to the database
                        try:
                            # Ping the MongoDB server to check connection
                            await client.admin.command('ping')
                        except Exception as e:
                            return {"error": f"Failed to connect to MongoDB: {str(e)}"}
                        
                        db = client.avatar_team_db
                        
                        # Check if project exists
                        project = await db.projects.find_one({"name": project_name})
                        if not project:
                            return {"error": f"Project {project_name} not found"}
                        
                        # Get all tasks for this project
                        try:
                            cursor = db.tasks.find({"project_name": project_name})
                            tasks = await cursor.to_list(length=100)
                        except Exception as e:
                            return {"error": f"Failed to retrieve tasks: {str(e)}"}
                        
                        return {
                            "status": "success",
                            "tasks": tasks
                        }
                    
                    except Exception as e:
                        return {"error": f"Unexpected error: {str(e)}"}
                    finally:
                        # Always close the client
                        client.close()
                
                try:
                    return loop.run_until_complete(run_with_new_client())
                except Exception as e:
                    return {"error": f"Event loop error: {str(e)}"}
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            # Execute in a separate thread with proper timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                try:
                    result = executor.submit(run_async_func).result(timeout=30)
                except concurrent.futures.TimeoutError:
                    return "Error retrieving tasks: Operation timed out after 30 seconds"
                except Exception as e:
                    return f"Error in thread execution: {str(e)}"
            
            # Check for errors
            if isinstance(result, dict) and "error" in result:
                return f"Error retrieving tasks: {result['error']}"
                
            tasks_data = result.get("tasks", [])
            
            # Create a response about task assignments
            task_list_items = []
            for t in tasks_data:
                name = t.get('name', 'Unnamed task')
                assigned_to = t.get('assigned_to', 'Unassigned')
                status = t.get('status', 'unknown').upper()
                task_list_items.append(f"- {name} (assigned to {assigned_to}, status: {status})")
            
            task_list = "\n".join(task_list_items)
            
            if not task_list:
                return "No tasks have been assigned yet. Would you like me to create some standard tasks?"
            
            return f"""Here are the current task assignments:
            
            {task_list}
            
            Would you like me to update any of these assignments?"""
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error retrieving tasks: {str(e)}\n{error_details}")
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
