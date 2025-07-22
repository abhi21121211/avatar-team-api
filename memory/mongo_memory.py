import asyncio
import threading
import inspect
from datetime import datetime
from typing import Dict, List, Any, Optional
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from utils.database import connect_to_mongodb

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set")

# Global tracking of event loop states
_event_loop_tls = threading.local()

class MongoSharedMemory:
    """Memory storage implementation using MongoDB"""
    
    def __init__(self):
        """Initialize the shared memory."""
        self.client = None
        self.db = None
        self.connected = False
        self._init_db()
    
    def _init_db(self):
        """Initialize the MongoDB connection"""
        if self.connected:
            return
        
        # Create the client
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client.avatar_team_db
        self.connected = True
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    async def _ensure_connected(self):
        """Ensure connection to MongoDB."""
        if not self.connected:
            self.db = await connect_to_mongodb()
            self.connected = True
            
    async def add_message(self, agent_name: str, user_message: str, agent_response: str, project_name: Optional[str] = None):
        """Add a message to the conversation history in MongoDB"""
        await self._ensure_connected()
        
        # Don't check self.db with a boolean condition
        if self.db is None:
            print("Error: Database connection not established")
            return False
            
        try:
            await self.db.conversations.insert_one({
                "agent": agent_name,
                "timestamp": datetime.now(),
                "user_message": user_message,
                "agent_response": agent_response,
                "project_name": project_name
            })
            return True
        except Exception as e:
            print(f"Error adding message to conversation: {str(e)}")
            return False
    
    async def get_conversation_history(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the conversation history for a specific agent from MongoDB"""
        await self._ensure_connected()
        
        cursor = self.db.conversations.find({"agent": agent_name}).sort("timestamp", -1).limit(limit)
        
        conversations = []
        async for doc in cursor:
            conversations.append({
                "timestamp": doc["timestamp"].isoformat(),
                "user_message": doc["user_message"],
                "agent_response": doc["agent_response"]
            })
        
        return conversations[::-1]  # Reverse to get chronological order
    
    async def get_all_conversations(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent conversations from all agents from MongoDB"""
        await self._ensure_connected()
        
        # Get unique agent names
        agents = set()
        # Changed from the async for cursor-based approach to a direct method call
        agent_names = await self.db.conversations.distinct("agent")
        agents.update(agent_names)
        
        result = {}
        for agent in agents:
            result[agent] = await self.get_conversation_history(agent, limit)
        
        return result
    
    async def add_context(self, key: str, value: Any):
        """Add or update a context entry in MongoDB"""
        await self._ensure_connected()
        
        # Use upsert to create or update
        await self.db.context.update_one(
            {"key": key},
            {"$set": {"value": value, "updated_at": datetime.now()}},
            upsert=True
        )
    
    async def get_context(self, key: Optional[str] = None) -> Any:
        """Get context entry or all context if key is None from MongoDB"""
        await self._ensure_connected()
        
        if key is None:
            # Get all context
            context = {}
            async for doc in self.db.context.find():
                context[doc["key"]] = doc["value"]
            return context
        
        # Get specific context
        doc = await self.db.context.find_one({"key": key})
        return doc["value"] if doc else None
    
    async def get_agent_context(self, agent_name: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Get all relevant context for an agent including its conversations and shared context"""
        await self._ensure_connected()
        
        if self.db is None:
            print("Error: Database connection not established")
            return {"error": "Database connection not established"}
        
        try:
            # Get this agent's conversations
            agent_conversations = await self.get_conversation_history(agent_name)
        except Exception as e:
            print(f"Error getting agent conversations: {str(e)}")
            agent_conversations = []
        
        try:
            # Get recent messages from all agents for shared context
            all_conversations = {}
            
            # Get recent messages from each agent
            async for agent_doc in self.db.conversations.aggregate([
                {"$match": {"agent": agent_name}},
                {"$group": {
                    "_id": "$agent",
                    "conversations": {"$push": {
                        "user_message": "$user_message",
                        "agent_response": "$agent_response",
                        "timestamp": "$timestamp"
                    }},
                }},
                {"$project": {
                    "agent": "$_id",
                    "conversations": {"$slice": ["$conversations", 3]}  # Get only the 3 most recent
                }}
            ]):
                agent = agent_doc["_id"]
                if agent != agent_name:  # Only include other agents
                    all_conversations[agent] = agent_doc["conversations"]
            
            # Get projects the agent is working on
            projects = set()
            async for doc in self.db.context.find({"agent": agent_name}).distinct("project_name"):
                if doc:
                    projects.add(doc)
            
            # Compile complete context
            context = {
                "agent": agent_name,
                "conversations": agent_conversations,
                "all_conversations": all_conversations,
                "projects": list(projects)
            }
            
            # Add current project context if specified
            if project_name:
                context["current_project"] = project_name
                
                # Add project tasks if available
                try:
                    tasks = []
                    async for task in self.db.tasks.find({"project_name": project_name, "assigned_to": agent_name}):
                        if "_id" in task:
                            del task["_id"]  # Remove MongoDB ID
                        tasks.append(task)
                    
                    if tasks:
                        context["tasks"] = tasks
                except Exception as e:
                    print(f"Error getting tasks for context: {str(e)}")
            
            return context
            
        except Exception as e:
            print(f"Error getting agent context: {str(e)}")
            return {"error": str(e)}
    
    def _run_async_in_sync_context(self, coro):
        """
        Run an async coroutine in a synchronous context safely.
        Handles the case where an event loop might already be running.
        """
        # Check if we're already in an async context
        if inspect.iscoroutinefunction(inspect.currentframe().f_back.f_code):
            # If we're called from an async function, just return the coroutine
            return coro
            
        # Check if we have a thread-local event loop already running
        loop = getattr(_event_loop_tls, 'loop', None)
        
        if loop is None or not loop.is_running():
            # If no loop or loop is not running, create a new one
            try:
                _event_loop_tls.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_event_loop_tls.loop)
                return _event_loop_tls.loop.run_until_complete(coro)
            finally:
                asyncio.set_event_loop(None)
                _event_loop_tls.loop = None
        else:
            # We're in a context where loop is already running, but not in an async function
            # Use a thread to run the coroutine
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
    
    def add_message_sync(self, agent_name: str, user_message: str, agent_response: str, project_name: Optional[str] = None):
        """Synchronous wrapper for add_message"""
        return self._run_async_in_sync_context(self.add_message(agent_name, user_message, agent_response, project_name))
    
    def get_conversation_history_sync(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_conversation_history"""
        return self._run_async_in_sync_context(self.get_conversation_history(agent_name, limit))
    
    def get_all_conversations_sync(self, limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Synchronous wrapper for get_all_conversations"""
        return self._run_async_in_sync_context(self.get_all_conversations(limit))
    
    def add_context_sync(self, key: str, value: Any):
        """Synchronous wrapper for add_context"""
        return self._run_async_in_sync_context(self.add_context(key, value))
    
    def get_context_sync(self, key: Optional[str] = None) -> Any:
        """Synchronous wrapper for get_context"""
        return self._run_async_in_sync_context(self.get_context(key))
    
    def get_agent_context_sync(self, agent_name: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous wrapper for get_agent_context"""
        return self._run_async_in_sync_context(self.get_agent_context(agent_name, project_name))

# Create a singleton instance
mongo_shared_memory = MongoSharedMemory()

# Compatibility with original SharedMemory
def add_message(agent_name, user_message, agent_response, project_name=None):
    return mongo_shared_memory.add_message_sync(agent_name, user_message, agent_response, project_name)

def get_conversation_history(agent_name, limit=10):
    return mongo_shared_memory.get_conversation_history_sync(agent_name, limit)

def get_all_conversations(limit=5):
    return mongo_shared_memory.get_all_conversations_sync(limit)

def add_context(key, value):
    return mongo_shared_memory.add_context_sync(key, value)

def get_context(key=None):
    return mongo_shared_memory.get_context_sync(key)

def get_agent_context(agent_name, project_name=None):
    return mongo_shared_memory.get_agent_context_sync(agent_name, project_name) 