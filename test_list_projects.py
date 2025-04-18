"""
Test script for listing projects from MongoDB.
This helps debug issues with project listing.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from utils.database import connect_to_mongodb, close_mongodb_connection, create_project, list_projects, get_project

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_list_projects():
    """Test listing projects from MongoDB"""
    logger.info("Starting project listing test...")
    
    try:
        # Connect to MongoDB
        db = await connect_to_mongodb()
        logger.info("Connected to MongoDB successfully")
        
        # Create a test project first
        test_project_name = "test_project_listing"
        test_project_description = "This is a test project for testing project listing"
        
        logger.info(f"Creating test project: {test_project_name}")
        await create_project(test_project_name, test_project_description)
        
        # List all projects
        logger.info("Listing all projects")
        projects = await list_projects()
        
        # Print project details
        logger.info(f"Found {len(projects)} projects:")
        for i, project in enumerate(projects):
            logger.info(f"  Project {i+1}: {project.name}")
            logger.info(f"  - Description: {project.description}")
            logger.info(f"  - Tasks: {len(project.tasks)}")
            logger.info(f"  - Files: {len(project.files)}")
        
        # Get a specific project
        logger.info(f"Getting specific project: {test_project_name}")
        project = await get_project(test_project_name)
        if project:
            logger.info(f"Successfully retrieved project: {project.name}")
        else:
            logger.error(f"Failed to retrieve project: {test_project_name}")
        
        # Clean up - delete test project
        result = await db.projects.delete_one({"name": test_project_name})
        if result.deleted_count:
            logger.info(f"Successfully deleted test project: {test_project_name}")
        else:
            logger.warning(f"Failed to delete test project: {test_project_name}")
        
        # Close MongoDB connection
        await close_mongodb_connection()
        
        return True
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Project listing test")
    success = asyncio.run(test_list_projects())
    
    if success:
        logger.info("✅ Project listing test completed successfully!")
        exit(0)
    else:
        logger.error("❌ Project listing test failed!")
        exit(1) 