from memory.shared_memory import SharedMemory, shared_memory
from memory.mongo_memory import MongoSharedMemory, mongo_shared_memory

# Use MongoDB memory as the default
default_memory = mongo_shared_memory
