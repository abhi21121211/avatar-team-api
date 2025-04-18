"""
Test script for creating a project in MongoDB.
This helps debug issues with project creation.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from utils.database import connect_to_mongodb, close_mongodb_connection, create_project

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_create_project():
    """Test creating a project in MongoDB"""
    logger.info("Starting project creation test...")
    
    try:
        # Connect to MongoDB
        db = await connect_to_mongodb()
        logger.info("Connected to MongoDB successfully")
        
        # Create a test project
        test_project_name = "test_project_creation"
        test_project_description = "This is a test project for testing project creation"
        
        logger.info(f"Creating test project: {test_project_name}")
        project = await create_project(test_project_name, test_project_description)
        
        logger.info(f"Project created successfully: {project.name}")
        logger.info(f"Project details: {project.dict()}")
        
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
        return False

if __name__ == "__main__":
    logger.info("Project creation test")
    success = asyncio.run(test_create_project())
    
    if success:
        logger.info("✅ Project creation test completed successfully!")
        exit(0)
    else:
        logger.error("❌ Project creation test failed!")
        exit(1) 