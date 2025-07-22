import os
import motor.motor_asyncio
from beanie import init_beanie
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import logging
from dotenv import load_dotenv
import uuid
from bson import ObjectId

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set")

# Check for placeholder password
if "<db_password>" in MONGODB_URI:
    error_message = (
        "\n\n" + "="*80 + "\n" +
        "CRITICAL ERROR: MongoDB password not configured!\n\n" +
        "You need to replace <db_password> in your .env file with your actual MongoDB password.\n" +
        "MONGODB_URI=mongodb+srv://abhishekdukare689:<db_password>@cluster0.8ijizu7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0\n\n" +
        "After updating the password, try running the application again.\n" +
        "="*80 + "\n"
    )
    raise ValueError(error_message)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models for MongoDB documents
class Task(BaseModel):
    id: str
    name: str
    description: str
    status: str = "pending"
    assigned_to: str
    created_at: datetime = datetime.now()
    updated_at: Optional[datetime] = None
    project_name: str

class File(BaseModel):
    path: str
    content: str
    project_name: str
    created_at: datetime = datetime.now()
    updated_at: Optional[datetime] = None

class Project(BaseModel):
    name: str
    description: str
    created_at: datetime = datetime.now()
    updated_at: Optional[datetime] = None
    tasks: List[Task] = []
    files: List[str] = []

class Conversation(BaseModel):
    agent: str
    user_message: str
    agent_response: str
    project_name: Optional[str] = None
    timestamp: datetime = datetime.now()

# MongoDB client
client = None
db = None

async def connect_to_mongodb():
    """Connect to MongoDB and initialize collections"""
    global client, db
    try:
        logger.info("Connecting to MongoDB...")
        
        # Create a Motor client
        client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000  # 5 second timeout for server selection
        )
        
        # Test the connection
        await client.admin.command('ping')
        
        db = client.avatar_team_db
        logger.info("Connected to MongoDB")
        
        # Initialize collections if they don't exist
        collections = await db.list_collection_names()
        
        # Ensure required collections exist
        if "projects" not in collections:
            logger.info("Creating projects collection")
            await db.create_collection("projects")
            
        if "tasks" not in collections:
            logger.info("Creating tasks collection")
            await db.create_collection("tasks")
            
        if "files" not in collections:
            logger.info("Creating files collection")
            await db.create_collection("files")
            
        if "conversations" not in collections:
            logger.info("Creating conversations collection")
            await db.create_collection("conversations")
            
        if "context" not in collections:
            logger.info("Creating context collection")
            await db.create_collection("context")

        if "team_names" not in collections:
            logger.info("Creating team_names collection")
            await db.create_collection("team_names")
        
        logger.info("MongoDB collections initialized")
        
        # Initialize collections
        await init_beanie(
            database=db,
            document_models=[
                # Register document models here when needed
            ]
        )
        
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongodb_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        logger.info("Closed MongoDB connection")

# Project operations
async def create_project(name: str, description: str) -> Project:
    """Create a new project in MongoDB"""
    logger.info(f"Creating project in MongoDB: {name}")
    project = Project(name=name, description=description)
    try:
        await db.projects.insert_one(project.dict())
        logger.info(f"Project created successfully: {name}")
        return project
    except Exception as e:
        logger.error(f"Error creating project {name}: {str(e)}")
        raise

async def get_project(name: str) -> Optional[Project]:
    """Get project details from MongoDB"""
    logger.info(f"Getting project from MongoDB: {name}")
    
    try:
        project_data = await db.projects.find_one({"name": name})
        if project_data:
            try:
                project = Project(**project_data)
                logger.info(f"Successfully retrieved project: {name}")
                return project
            except Exception as e:
                logger.error(f"Error parsing project data for {name}: {str(e)}")
                logger.error(f"Project data: {project_data}")
                raise
        else:
            logger.warning(f"Project not found: {name}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving project {name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

async def list_projects() -> List[Project]:
    """List all projects from MongoDB"""
    logger.info("Listing all projects from MongoDB")
    
    try:
        projects = []
        async for project_data in db.projects.find():
            try:
                project = Project(**project_data)
                projects.append(project)
            except Exception as e:
                logger.error(f"Error parsing project data: {str(e)}, data: {project_data}")
                # Continue with other projects even if one fails
                continue
                
        logger.info(f"Found {len(projects)} projects")
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# Task operations
async def add_task(project_name: str, task_data: Dict[str, Any]) -> Task:
    """Add a task to a project in MongoDB"""
    task = Task(
        id=task_data.get("id"),
        name=task_data.get("name"),
        description=task_data.get("description"),
        assigned_to=task_data.get("assigned_to"),
        project_name=project_name
    )
    
    await db.tasks.insert_one(task.dict())
    
    # Update project tasks reference
    await db.projects.update_one(
        {"name": project_name},
        {"$push": {"tasks": task.id}}
    )
    
    return task

async def update_task_status(project_name: str, task_id: str, status: str) -> Dict[str, Any]:
    """Update a task's status in MongoDB"""
    try:
        logger.info(f"Updating task {task_id} status to {status} for project {project_name}")
        
        # Update task in the tasks collection
        result = await db.tasks.update_one(
            {"id": task_id, "project_name": project_name},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )
        
        # If task was not found/updated in the tasks collection
        if result.matched_count == 0:
            logger.warning(f"Task {task_id} not found in tasks collection, checking project document")
            
            # Check if the task exists in the project document
            project = await get_project(project_name)
            if not project:
                logger.error(f"Project {project_name} not found")
                raise ValueError(f"Project {project_name} not found")
            
            # Find and update the task in the project's tasks array
            task_found = False
            if hasattr(project, 'tasks'):
                for task in project.tasks:
                    if task.get("id") == task_id:
                        # Found the task, update it
                        task["status"] = status
                        task["updated_at"] = datetime.now()
                        task_found = True
                        
                        # Also add to tasks collection for future use
                        task_copy = task.copy()
                        task_copy["project_name"] = project_name
                        await db.tasks.insert_one(task_copy)
                        break
                
                if task_found:
                    # Update the project document with the modified tasks
                    await db.projects.update_one(
                        {"name": project_name},
                        {"$set": {"tasks": project.tasks, "updated_at": datetime.now()}}
                    )
            
            if not task_found:
                logger.error(f"Task {task_id} not found for project {project_name}")
                raise ValueError(f"Task {task_id} not found in project {project_name}")
        
        # Get the updated task to return
        updated_task = await db.tasks.find_one({"id": task_id, "project_name": project_name})
        if updated_task:
            # Remove MongoDB _id field
            if "_id" in updated_task:
                del updated_task["_id"]
            logger.info(f"Successfully updated task {task_id}")
            return updated_task
        else:
            # Fallback to searching in project
            project = await get_project(project_name)
            if hasattr(project, 'tasks'):
                for task in project.tasks:
                    if task.get("id") == task_id:
                        task_copy = task.copy()
                        task_copy["project_name"] = project_name
                        return task_copy
            
            raise ValueError(f"Task {task_id} not found after update")
    except ValueError as ve:
        # Re-raise ValueError for proper error handling
        raise ve
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# File operations
async def create_or_update_file(project_name: str, file_path: str, content: str) -> File:
    """Create or update a file in MongoDB"""
    file = File(
        path=file_path,
        content=content,
        project_name=project_name,
    )
    
    # Check if file exists
    existing_file = await db.files.find_one({"path": file_path, "project_name": project_name})
    
    if existing_file:
        # Update existing file
        await db.files.update_one(
            {"path": file_path, "project_name": project_name},
            {"$set": {"content": content, "updated_at": datetime.now()}}
        )
    else:
        # Insert new file
        await db.files.insert_one(file.dict())
        # Update project files reference
        await db.projects.update_one(
            {"name": project_name},
            {"$push": {"files": file_path}}
        )
    
    return file

async def get_file(project_name: str, file_path: str) -> Optional[str]:
    """Get file content from MongoDB"""
    file_data = await db.files.find_one({"path": file_path, "project_name": project_name})
    return file_data["content"] if file_data else None

# Conversation operations
async def store_conversation(agent: str, user_message: str, agent_response: str, project_name: Optional[str] = None):
    """Store a conversation in MongoDB"""
    conversation = Conversation(
        agent=agent,
        user_message=user_message,
        agent_response=agent_response,
        project_name=project_name
    )
    
    await db.conversations.insert_one(conversation.dict())
    return conversation

async def get_conversations(agent: str, project_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get conversations for an agent, optionally filtered by project"""
    query = {"agent": agent}
    if project_name:
        query["project_name"] = project_name
    
    conversations = []
    async for conversation in db.conversations.find(query).sort("timestamp", 1):
        conversations.append({
            "role": "user",
            "content": conversation["user_message"]
        })
        conversations.append({
            "role": "agent",
            "content": conversation["agent_response"]
        })
    
    return conversations

async def get_project_tasks(project_name: str) -> List[Dict[str, Any]]:
    """Get tasks for a specific project from MongoDB"""
    try:
        logger.info(f"Getting tasks for project {project_name}")
        # First check if we have tasks in the separate tasks collection
        tasks = []
        async for task in db.tasks.find({"project_name": project_name}):
            # Remove MongoDB _id field
            if "_id" in task:
                del task["_id"]
            tasks.append(task)
        
        # If no tasks found, try to get them from the project document
        if not tasks:
            project = await get_project(project_name)
            if project and hasattr(project, 'tasks') and project.tasks:
                tasks = project.tasks
                # Add project_name to each task if not present
                for task in tasks:
                    if "project_name" not in task:
                        task["project_name"] = project_name
        
        logger.info(f"Found {len(tasks)} tasks for project {project_name}")
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks for project {project_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

async def plan_project(project_name: str) -> Dict[str, Any]:
    """Create a project plan with tasks for team members."""
    try:
        logger.info(f"Creating plan for project {project_name}")
        
        # Check if project exists
        project = await get_project(project_name)
        if not project:
            logger.error(f"Project {project_name} not found")
            raise ValueError(f"Project {project_name} not found")
        
        # Create standard tasks for each team role
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
        
        # Insert tasks into MongoDB
        for task in tasks:
            await db.tasks.insert_one(task)
        
        # Update project with task references
        task_ids = [task["id"] for task in tasks]
        await db.projects.update_one(
            {"name": project_name},
            {"$set": {"has_plan": True, "updated_at": datetime.now()}}
        )
        
        logger.info(f"Successfully created plan with {len(tasks)} tasks for project {project_name}")
        
        return {
            "status": "success",
            "project_name": project_name,
            "task_count": len(tasks)
        }
    except Exception as e:
        logger.error(f"Error creating plan for project {project_name}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# Define team member name model
async def create_team_member_name(role: str, name: str):
    """Create or update a team member name mapping"""
    try:
        global client, db
        if not client:
            await connect_to_mongodb()
        
        # Check if the role already exists
        existing = await db.team_names.find_one({"role": role})
        
        if existing:
            # Update existing name
            await db.team_names.update_one(
                {"role": role},
                {"$set": {"name": name, "updated_at": datetime.now()}}
            )
        else:
            # Create new name
            await db.team_names.insert_one({
                "role": role,
                "name": name,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
        
        return {"role": role, "name": name}
    except Exception as e:
        print(f"Error in create_team_member_name: {str(e)}")
        raise e

async def get_team_member_name(role: str) -> Optional[Dict[str, Any]]:
    """Get a team member's custom name by role"""
    try:
        global client, db
        if not client:
            await connect_to_mongodb()
        
        result = await db.team_names.find_one({"role": role})
        if not result:
            return None
            
        return {
            "role": result["role"],
            "name": result["name"]
        }
    except Exception as e:
        print(f"Error in get_team_member_name: {str(e)}")
        return None

async def get_all_team_member_names() -> List[Dict[str, Any]]:
    """Get all team member custom names"""
    try:
        global client, db
        if not client:
            await connect_to_mongodb()
        
        cursor = db.team_names.find({})
        names = []
        async for doc in cursor:
            names.append({
                "role": doc["role"],
                "name": doc["name"]
            })
        return names
    except Exception as e:
        print(f"Error in get_all_team_member_names: {str(e)}")
        return []

async def delete_team_member_name(role: str) -> bool:
    """Delete a team member custom name"""
    try:
        global client, db
        if not client:
            await connect_to_mongodb()
        
        result = await db.team_names.delete_one({"role": role})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error in delete_team_member_name: {str(e)}")
        return False 