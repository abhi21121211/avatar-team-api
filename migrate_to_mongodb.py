"""
Script to migrate existing data from file-based storage to MongoDB.
This should be run once before switching to the MongoDB-based implementation.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from utils.database import connect_to_mongodb, close_mongodb_connection
from memory.shared_memory import SharedMemory
from memory.mongo_memory import MongoSharedMemory
from utils.project_manager import ProjectManager
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize file-based components
file_memory = SharedMemory()
file_project_manager = ProjectManager("projects")

# Initialize MongoDB-based components
mongo_memory = MongoSharedMemory()

async def migrate_memory():
    """Migrate memory data from file to MongoDB"""
    logger.info("Migrating memory data...")
    
    # Load memory from file
    memory_data = file_memory._load_memory()
    
    # Migrate conversations
    for agent_name, conversations in memory_data.get("conversations", {}).items():
        logger.info(f"Migrating {len(conversations)} conversations for agent {agent_name}")
        
        for conversation in conversations:
            await mongo_memory.add_message(
                agent_name,
                conversation.get("user_message", ""),
                conversation.get("agent_response", "")
            )
    
    # Migrate context
    for key, value in memory_data.get("context", {}).items():
        logger.info(f"Migrating context: {key}")
        await mongo_memory.add_context(key, value)
    
    logger.info("Memory migration completed")

async def migrate_projects():
    """Migrate projects from file to MongoDB"""
    logger.info("Migrating projects...")
    
    # Get list of projects
    project_names = file_project_manager.list_projects()
    logger.info(f"Found {len(project_names)} projects to migrate")
    
    for project_name in project_names:
        logger.info(f"Migrating project: {project_name}")
        
        try:
            # Get project details
            project_data = file_project_manager.get_project(project_name)
            
            # Create project in MongoDB
            from utils.database import create_project
            project = await create_project(
                project_name,
                project_data.get("description", "")
            )
            
            # Migrate files
            files = file_project_manager.list_files(project_name)
            logger.info(f"Migrating {len(files)} files for project {project_name}")
            
            for file_path in files:
                try:
                    # Read file content
                    content = file_project_manager.read_file(project_name, file_path)
                    
                    # Create file in MongoDB
                    from utils.database import create_or_update_file
                    await create_or_update_file(project_name, file_path, content)
                    
                    logger.info(f"Migrated file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to migrate file {file_path}: {str(e)}")
            
            # Migrate tasks
            tasks = project_data.get("tasks", [])
            logger.info(f"Migrating {len(tasks)} tasks for project {project_name}")
            
            for task in tasks:
                try:
                    # Create task in MongoDB
                    from utils.database import add_task
                    await add_task(project_name, {
                        "id": task.get("id"),
                        "name": task.get("name"),
                        "description": task.get("description"),
                        "assigned_to": task.get("assigned_to"),
                        "status": task.get("status", "pending")
                    })
                    
                    logger.info(f"Migrated task: {task.get('name')}")
                except Exception as e:
                    logger.error(f"Failed to migrate task {task.get('name')}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to migrate project {project_name}: {str(e)}")
    
    logger.info("Project migration completed")

async def main():
    """Main migration function"""
    logger.info("Starting migration to MongoDB...")
    
    # Connect to MongoDB
    db = await connect_to_mongodb()
    
    # Perform migrations
    await migrate_memory()
    await migrate_projects()
    
    # Close MongoDB connection
    await close_mongodb_connection()
    
    logger.info("Migration completed successfully")

if __name__ == "__main__":
    asyncio.run(main()) 