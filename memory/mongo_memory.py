import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import motor.motor_asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI environment variable is not set")

class MongoSharedMemory:
    """Memory storage implementation using MongoDB"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.initialized = False
        self._init_db()
    
    def _init_db(self):
        """Initialize the MongoDB connection"""
        if self.initialized:
            return
        
        # Create the client
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client.avatar_team_db
        self.initialized = True
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    async def add_message(self, agent_name: str, user_message: str, agent_response: str):
        """Add a message to the conversation history in MongoDB"""
        self._init_db()
        
        conversation = {
            "agent": agent_name,
            "timestamp": datetime.now(),
            "user_message": user_message,
            "agent_response": agent_response
        }
        
        await self.db.conversations.insert_one(conversation)
    
    async def get_conversation_history(self, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the conversation history for a specific agent from MongoDB"""
        self._init_db()
        
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
        self._init_db()
        
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
        self._init_db()
        
        # Use upsert to create or update
        await self.db.context.update_one(
            {"key": key},
            {"$set": {"value": value, "updated_at": datetime.now()}},
            upsert=True
        )
    
    async def get_context(self, key: Optional[str] = None) -> Any:
        """Get context entry or all context if key is None from MongoDB"""
        self._init_db()
        
        if key is None:
            # Get all context
            context = {}
            async for doc in self.db.context.find():
                context[doc["key"]] = doc["value"]
            return context
        
        # Get specific context
        doc = await self.db.context.find_one({"key": key})
        return doc["value"] if doc else None
    
    async def get_agent_context(self, agent_name: str) -> Dict[str, Any]:
        """Get all relevant context for an agent including its conversations and shared context"""
        try:
            all_conversations = await self.get_all_conversations()
        except Exception as e:
            print(f"Error getting all conversations: {str(e)}")
            all_conversations = {}
            
        try:
            context = await self.get_context()
        except Exception as e:
            print(f"Error getting shared context: {str(e)}")
            context = {}
        
        try:
            # Get this agent's conversations
            agent_conversations = await self.get_conversation_history(agent_name)
        except Exception as e:
            print(f"Error getting agent conversations: {str(e)}")
            agent_conversations = []
        
        return {
            "agent_conversations": agent_conversations,
            "all_conversations": all_conversations,
            "shared_context": context
        }
    
    def _run_async_in_sync_context(self, coro):
        """Helper method to run async code in a synchronous context."""
        try:
            # Simply use asyncio.run which handles event loop creation and cleanup
            return asyncio.run(coro)
        except RuntimeError as e:
            # This happens when there's already a running event loop
            # We'll get the current event loop and use run_until_complete
            # if possible, or create a new loop if necessary
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(coro)
            except RuntimeError:
                # If we can't get the current event loop, create a new one
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    # Always close the loop we created to prevent memory leaks
                    new_loop.close()
                    # Reset the event loop to None to avoid conflicts
                    asyncio.set_event_loop(None)
    
    def add_message_sync(self, agent_name: str, user_message: str, agent_response: str):
        """Synchronous wrapper for add_message"""
        return self._run_async_in_sync_context(self.add_message(agent_name, user_message, agent_response))
    
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
    
    def get_agent_context_sync(self, agent_name: str) -> Dict[str, Any]:
        """Synchronous wrapper for get_agent_context"""
        return self._run_async_in_sync_context(self.get_agent_context(agent_name))

# Create a singleton instance
mongo_shared_memory = MongoSharedMemory()

# Compatibility with original SharedMemory
def add_message(agent_name, user_message, agent_response):
    return mongo_shared_memory.add_message_sync(agent_name, user_message, agent_response)

def get_conversation_history(agent_name, limit=10):
    return mongo_shared_memory.get_conversation_history_sync(agent_name, limit)

def get_all_conversations(limit=5):
    return mongo_shared_memory.get_all_conversations_sync(limit)

def add_context(key, value):
    return mongo_shared_memory.add_context_sync(key, value)

def get_context(key=None):
    return mongo_shared_memory.get_context_sync(key)

def get_agent_context(agent_name):
    return mongo_shared_memory.get_agent_context_sync(agent_name) 