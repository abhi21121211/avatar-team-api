"""
Script to test MongoDB connection and basic operations.
Run this script to ensure MongoDB is properly configured.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from utils.database import connect_to_mongodb, close_mongodb_connection, create_project, get_project

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def test_mongodb_connection():
    """Test MongoDB connection and perform basic operations"""
    logger.info("Testing MongoDB connection...")
    
    try:
        # Connect to MongoDB
        db = await connect_to_mongodb()
        logger.info("✅ Successfully connected to MongoDB")
        
        # Test basic operations
        logger.info("Testing basic operations...")
        
        # Create a test project
        test_project_name = "mongodb_test_project"
        test_project = await create_project(test_project_name, "Test project for MongoDB connection")
        logger.info(f"✅ Successfully created test project: {test_project_name}")
        
        # Retrieve the test project
        retrieved_project = await get_project(test_project_name)
        if retrieved_project and retrieved_project.name == test_project_name:
            logger.info(f"✅ Successfully retrieved test project: {test_project_name}")
        else:
            logger.error("❌ Failed to retrieve test project")
        
        # Clean up - delete test project
        await db.projects.delete_one({"name": test_project_name})
        logger.info(f"✅ Successfully deleted test project: {test_project_name}")
        
        # Close MongoDB connection
        await close_mongodb_connection()
        logger.info("✅ Successfully closed MongoDB connection")
        
        logger.info("All MongoDB tests passed successfully! 🎉")
        
    except Exception as e:
        logger.error(f"❌ Error during MongoDB testing: {str(e)}")
        logger.error("Please check your MongoDB connection string and credentials.")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_mongodb_connection())
    if not success:
        exit(1) 