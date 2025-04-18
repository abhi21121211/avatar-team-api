# MongoDB Integration for Avatar Team API

This document explains the MongoDB integration for the Avatar Team API project.

## Overview

The project has been updated to use MongoDB as the primary data store instead of file-based storage. This provides:

1. Better scalability
2. Improved data querying capabilities
3. Separation of data storage from application logic
4. Support for concurrent operations
5. Enhanced security

## Files Added/Modified

### New Files:

- `utils/database.py` - MongoDB connection and data operations
- `utils/project_manager_mongo.py` - MongoDB-based project manager
- `memory/mongo_memory.py` - MongoDB-based shared memory
- `migrate_to_mongodb.py` - Script to migrate existing data to MongoDB
- `test_mongodb.py` - Test script for MongoDB connection

### Modified Files:

- `main.py` - Updated to use MongoDB-based project manager
- `agents/base_agent.py` - Updated to use MongoDB-based shared memory
- `memory/__init__.py` - Updated to expose MongoDB memory as default
- `.env` - Added MongoDB connection string
- `requirements.txt` - Added MongoDB-related packages

## Configuration

The MongoDB connection is configured through the `.env` file using the `MONGODB_URI` variable. Before using the application:

1. In `.env`, replace `<db_password>` in the MongoDB connection string with your actual password:

   ```
   MONGODB_URI=mongodb+srv://abhishekdukare689:<db_password>@cluster0.8ijizu7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
   ```

2. Ensure you have the required dependencies installed:
   ```
   pip install beanie motor pymongo
   ```

## Data Model

The following data models have been implemented:

1. **Project** - Represents a software project

   - Name, description, creation/update timestamps
   - References to tasks and files

2. **Task** - Represents a task assigned to an agent

   - ID, name, description, status
   - Assigned agent, project reference
   - Creation/update timestamps

3. **File** - Represents a file in a project

   - Path, content, project reference
   - Creation/update timestamps

4. **Conversation** - Represents agent-user conversations
   - Agent, user message, agent response
   - Project reference (optional)
   - Timestamp

## Migration

To migrate existing data from file-based storage to MongoDB:

1. Configure the MongoDB connection string in `.env` as described above
2. Run the migration script:
   ```
   python migrate_to_mongodb.py
   ```

This will:

- Migrate all existing projects, files, and tasks
- Migrate agent conversations and context
- Preserve all relationships between entities

## Testing

To test the MongoDB connection and basic operations:

```
python test_mongodb.py
```

This script verifies:

- Connection to MongoDB
- Basic CRUD operations (create, read, update, delete)
- Error handling

## Hybrid Approach

The implementation uses a hybrid approach that:

1. Maintains file storage on disk for compatibility
2. Stores data in MongoDB for improved access and querying
3. Falls back to file system when MongoDB data is not available

This ensures a smooth transition and maintains backward compatibility.

## Future Improvements

Potential future improvements:

1. Implement data validation using Beanie documents
2. Add indexing for improved performance
3. Implement data caching
4. Add support for MongoDB transactions
5. Implement versioning for files and projects
