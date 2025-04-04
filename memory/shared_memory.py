import os
import json
from datetime import datetime

class SharedMemory:
    def __init__(self):
        self.memory_file = os.path.join(os.path.dirname(__file__), "shared_memory.json")
        self._initialize_memory()
        
    def _initialize_memory(self):
        """Initialize the memory file if it doesn't exist"""
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w") as f:
                json.dump({
                    "conversations": {},
                    "context": {},
                    "last_updated": str(datetime.now())
                }, f, indent=2)
    
    def _load_memory(self):
        """Load the memory from the file"""
        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)
        except:
            self._initialize_memory()
            with open(self.memory_file, "r") as f:
                return json.load(f)
    
    def _save_memory(self, memory_data):
        """Save the memory to the file"""
        memory_data["last_updated"] = str(datetime.now())
        with open(self.memory_file, "w") as f:
            json.dump(memory_data, f, indent=2)
    
    def add_message(self, agent_name, user_message, agent_response):
        """Add a message to the conversation history"""
        memory = self._load_memory()
        
        if agent_name not in memory["conversations"]:
            memory["conversations"][agent_name] = []
            
        memory["conversations"][agent_name].append({
            "timestamp": str(datetime.now()),
            "user_message": user_message,
            "agent_response": agent_response
        })
        
        self._save_memory(memory)
    
    def get_conversation_history(self, agent_name, limit=10):
        """Get the conversation history for a specific agent"""
        memory = self._load_memory()
        
        if agent_name not in memory["conversations"]:
            return []
            
        return memory["conversations"][agent_name][-limit:]
    
    def get_all_conversations(self, limit=5):
        """Get recent conversations from all agents"""
        memory = self._load_memory()
        result = {}
        
        for agent, conversations in memory["conversations"].items():
            result[agent] = conversations[-limit:]
            
        return result
    
    def add_context(self, key, value):
        """Add or update a context entry"""
        memory = self._load_memory()
        memory["context"][key] = value
        self._save_memory(memory)
    
    def get_context(self, key=None):
        """Get context entry or all context if key is None"""
        memory = self._load_memory()
        
        if key is None:
            return memory["context"]
        
        return memory["context"].get(key, None)
    
    def get_agent_context(self, agent_name):
        """Get all relevant context for an agent including its conversations and shared context"""
        all_conversations = self.get_all_conversations()
        context = self.get_context()
        
        # Get this agent's conversations
        agent_conversations = self.get_conversation_history(agent_name)
        
        return {
            "agent_conversations": agent_conversations,
            "all_conversations": all_conversations,
            "shared_context": context
        }

# Create a singleton instance
shared_memory = SharedMemory() 