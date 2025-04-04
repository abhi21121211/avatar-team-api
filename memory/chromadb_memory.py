import chromadb

class MemoryStorage:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="memory/")
        self.collection = self.client.get_or_create_collection("avatar_project")

    def save_task_result(self, task_name, result):
        self.collection.add(ids=[task_name], documents=[result])

    def get_task_result(self, task_name):
        results = self.collection.get(ids=[task_name])
        return results["documents"][0] if results["documents"] else None


client = chromadb.PersistentClient(path="path/to/chromadb")

# List collections
collections = client.list_collections()
for col in collections:
    print(col.name)