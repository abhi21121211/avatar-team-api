import sys
import os
import asyncio
import zipfile
import tempfile
from fastapi import FastAPI, Body, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import uvicorn
from agents.chief_architect import ChiefArchitect
from agents.frontend_engineer import FrontendEngineer
from agents.backend_engineer import BackendEngineer
from agents.devops_engineer import DevOpsEngineer
from agents.ai_ml_engineer import aIMLEngineer
from agents.product_manager import ProductManager
from agents.ui_ux_designer import uIUXDesigner
from agents.technical_writer import TechnicalWriter
from agents.customer_success import CustomerSuccess
from agents.legal_compliance import LegalCompliance
from agents.marketing_sales import MarketingSales
from utils.project_manager_mongo import MongoProjectManager
from utils.llm_manager import llm_manager, ModelProvider
from utils.database import connect_to_mongodb, close_mongodb_connection, create_project as db_create_project, list_projects as db_list_projects, get_project as db_get_project, get_project_tasks, plan_project as db_plan_project, update_task_status
from utils.helpers import serialize_model

# Ensure Python recognizes the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()

# Add CORS middleware to allow cross-origin requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Startup event to connect to MongoDB
@app.on_event("startup")
async def startup_db_client():
    app.mongodb = await connect_to_mongodb()

# Shutdown event to close MongoDB connection
@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongodb_connection()

# Initialize project manager with MongoDB support
project_manager = MongoProjectManager("projects")

# Initialize agents
agents = {
    "chiefArchitect": ChiefArchitect(),
    "frontendEngineer": FrontendEngineer(),
    "backendEngineer": BackendEngineer(),
    "devopsEngineer": DevOpsEngineer(),
    "aiMlEngineer": aIMLEngineer(),
    "productManager": ProductManager(),
    "uiUxDesigner": uIUXDesigner(),
    "technicalWriter": TechnicalWriter(),
    "customerSuccess": CustomerSuccess(),
    "legalCompliance": LegalCompliance(),
    "marketingSales": MarketingSales()
}

# Set project manager for all agents
for agent in agents.values():
    agent.project_manager = project_manager

# Define request models
class ChatRequest(BaseModel):
    message: str
    agent: str
    project: Optional[str] = None

class TaskRequest(BaseModel):
    task: str
    agent: str

class ProjectRequest(BaseModel):
    name: str
    description: str

class ImportProjectRequest(BaseModel):
    source_directory: str
    project_name: str
    description: str

class FileRequest(BaseModel):
    project_name: str
    file_path: str
    content: str

class FilePathRequest(BaseModel):
    project_name: str
    file_path: str

class TaskUpdateRequest(BaseModel):
    project_name: str
    task_id: str
    status: str

# Add new request models for LLM settings
class LLMProviderRequest(BaseModel):
    provider: str

class LLMModelRequest(BaseModel):
    provider: str
    model: str

# Define tasks for each agent
tasks = {
    "chiefArchitect": "Design the microservices architecture.",
    "frontendEngineer": "Develop the frontend using Next.js.",
    "backendEngineer": "Create backend APIs for data handling.",
    "devopsEngineer": "Set up CI/CD pipelines.",
    "aiMlEngineer": "Implement AI-based recommendations.",
    "productManager": "Define project scope and requirements.",
    "uiUxDesigner": "Design user-friendly UI mockups.",
    "technicalWriter": "Write documentation and guides.",
    "customerSuccess": "Ensure customer onboarding and support.",
    "legalCompliance": "Ensure project follows regulations.",
    "marketingSales": "Create marketing campaigns."
}

# API Endpoints for Project Management
@app.post("/api/projects")
async def create_project(request: ProjectRequest):
    """Create a new project."""
    try:
        # Use the async version directly
        project = await db_create_project(request.name, request.description)
        
        # Also create directory structure for compatibility
        project_dir = os.path.join(project_manager.base_directory, request.name)
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
            os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
            os.makedirs(os.path.join(project_dir, "docs"), exist_ok=True)
        
        # Set as current project
        project_manager.current_project = request.name
        
        # Convert project to dict using helper
        project_data = serialize_model(project)
        
        return {"status": "success", "project": project_data}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating project: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects")
async def list_projects():
    """List all projects."""
    try:
        # Use async db function directly
        projects = await db_list_projects()
        
        # Convert each project to dict using helper
        project_list = [serialize_model(project) for project in projects]
        
        return {"status": "success", "projects": project_list}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error listing projects: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_name}")
async def  get_project(project_name: str):
    """Get project details."""
    try:
        # Use async db function directly
        project = await db_get_project(project_name)
        
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_name} not found")
        
        # Convert project to dict using helper
        project_data = serialize_model(project)
            
        return {"status": "success", "project": project_data}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error getting project {project_name}: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_name}/plan")
async def plan_project(project_name: str):
    """Create a project plan with tasks for team members."""
    try:
        result = await db_plan_project(project_name)
        return {"status": "success", "plan": result}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating plan for project {project_name}: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/import")
async def import_project(request: ImportProjectRequest):
    """Import an existing project directory."""
    try:
        # Normalize path for Windows
        source_dir = request.source_directory.replace('\\', '/')
        
        # Validate path exists
        if not os.path.exists(source_dir):
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "detail": f"Source directory '{source_dir}' does not exist. Please provide a valid path."
                }
            )
        
        # Check if it's a directory
        if not os.path.isdir(source_dir):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "detail": f"Path '{source_dir}' is not a directory. Please provide a valid project directory."
                }
            )
            
        # Validate project name doesn't already exist
        project_dir = os.path.join(project_manager.base_directory, request.project_name)
        if os.path.exists(project_dir):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "detail": f"Project '{request.project_name}' already exists. Please choose a different name."
                }
            )
        
        # Import the project
        try:
            project = project_manager.import_existing_project(
                source_dir, 
                request.project_name, 
                request.description
            )
            return {"status": "success", "project": project}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "detail": f"Error importing project: {str(e)}"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/upload")
async def upload_project(
    project_name: str = Form(...),
    description: str = Form(...),
    project_file: UploadFile = File(...)
):
    """Upload a project as a zip file and import it."""
    try:
        # Validate file is a zip
        if not project_file.filename.endswith('.zip'):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "detail": "Only zip files are supported. Please upload a .zip file."
                }
            )
        
        # Validate project name doesn't already exist
        project_dir = os.path.join(project_manager.base_directory, project_name)
        if os.path.exists(project_dir):
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "detail": f"Project '{project_name}' already exists. Please choose a different name."
                }
            )
            
        # Create a temporary directory to extract the zip
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save the uploaded zip file
            temp_zip = os.path.join(temp_dir, "project.zip")
            with open(temp_zip, "wb") as f:
                contents = await project_file.read()
                f.write(contents)
            
            # Extract the zip file
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            try:
                with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except zipfile.BadZipFile:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "detail": "Invalid zip file. The file could not be extracted."
                    }
                )
            
            # Find the root directory of the project
            contents = os.listdir(extract_dir)
            source_dir = extract_dir
            
            # If zip contains a single directory, use it as the root
            if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
                source_dir = os.path.join(extract_dir, contents[0])
            
            # Import the project
            try:
                project = project_manager.import_existing_project(
                    source_dir, 
                    project_name, 
                    description
                )
                return {"status": "success", "project": project}
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "error",
                        "detail": f"Error importing project: {str(e)}"
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Endpoints for File Operations
@app.post("/api/files")
async def create_file(request: FileRequest):
    """Create a new file in a project."""
    try:
        file = project_manager.create_file(
            request.project_name,
            request.file_path,
            request.content
        )
        return {"status": "success", "file": file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
async def get_file(project_name: str, file_path: str):
    """Get the content of a file."""
    try:
        content = project_manager.read_file(project_name, file_path)
        return {"status": "success", "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {file_path} not found in project {project_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/files")
async def update_file(request: FileRequest):
    """Update the content of a file."""
    try:
        file = project_manager.update_file(
            request.project_name,
            request.file_path,
            request.content
        )
        return {"status": "success", "file": file}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {request.file_path} not found in project {request.project_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files")
async def delete_file(request: FilePathRequest):
    """Delete a file from a project."""
    try:
        result = project_manager.delete_file(request.project_name, request.file_path)
        return {"status": "success", "result": result}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {request.file_path} not found in project {request.project_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{project_name}")
async def list_files(project_name: str, directory: str = ""):
    """List files in a project directory."""
    try:
        files = project_manager.list_files(project_name, directory)
        return {"status": "success", "files": files}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Directory {directory} not found in project {project_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Endpoints for Task Management
@app.post("/api/tasks")
async def add_task(project_name: str, task: Dict[str, Any] = Body(...)):
    """Add a task to a project."""
    try:
        task = project_manager.add_task(project_name, task)
        return {"status": "success", "task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks")
async def update_task(request: TaskUpdateRequest):
    """Update a task's status."""
    try:
        updated_task = await update_task_status(request.project_name, request.task_id, request.status)
        return {"status": "success", "task": updated_task}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error updating task status: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{project_name}")
async def get_tasks(project_name: str):
    """Get all tasks in a project."""
    try:
        tasks = await get_project_tasks(project_name)
        if tasks is None:
            raise HTTPException(status_code=404, detail=f"Project {project_name} not found")
        return {"status": "success", "tasks": tasks}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error getting tasks for project {project_name}: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

# Original API Endpoints
async def execute_tasks():
    results = {}
    for role, agent in agents.items():
        task = tasks.get(role, "No specific task assigned.")
        print(f"🛠️ [{role}] Task: {task} ...")
        result = await agent.execute(task)
        results[role] = result
        print(f"✅ [{role}] Task completed!")
    return results

@app.get("/")
async def run_avatar_team():
    """API Endpoint to execute all agent tasks asynchronously."""
    results = await execute_tasks()
    return {"status": "All agents executed successfully!", "results": results}

@app.post("/api/execute")
async def execute_task(request: TaskRequest):
    try:
        agent = agents.get(request.agent)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {request.agent} not found")
        
        result = await agent.execute(request.task)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_with_agent(request: ChatRequest):
    """Chat with a specific agent."""
    print(f"Chat request received: {request}")
    try:
        if request.agent not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {request.agent} not found")
        
        # Use the LLM manager to generate the response
        agent_obj = agents[request.agent]
        
        # Set the current project for the agent if provided
        project_context = {}
        agent_tasks = []
        
        if request.project:
            project_manager.current_project = request.project
            
            # Get project details and agent-specific tasks
            try:
                project_context = await project_manager.get_project(request.project)
                # Fix: Don't use await with list comprehension
                agent_tasks = [task for task in project_context.get("tasks", []) 
                               if task.get("assigned_to") == request.agent]
            except Exception as e:
                print(f"Error getting project context: {str(e)}")
        
        # Modify the agent to use the current LLM provider and model
        provider = llm_manager.get_current_provider()
        model = llm_manager.get_current_model(provider)
        
        # Prepare context for the agent
        context = {
            "role": agent_obj.role,
            "goal": agent_obj.goal,
            "backstory": agent_obj.backstory
        }
        
        if request.project:
            context["current_project"] = request.project
            context["project_details"] = project_context
            context["my_tasks"] = agent_tasks
        
        # Create a prompt that includes project context if available
        prompt = request.message
        if request.project:
            prompt = f"""
You are working on the project "{request.project}".
Project description: {project_context.get('description', 'No description available')}

Your assigned tasks:
{format_tasks(agent_tasks)}

As {formatAgentName(request.agent)}, with your expertise and role, please respond to:
{request.message}
"""
        
        # Generate response using the selected provider/model with context
        response = llm_manager.generate_response(
            prompt,
            provider=provider,
            model=model,
            context=context
        )
        
        # Store the conversation in the agent
        agent_obj.add_conversation("user", request.message)
        agent_obj.add_conversation("agent", response)
        
        return {
            "status": "success", 
            "response": response,
            "agent": request.agent,
            "llm_info": {
                "provider": provider,
                "model": model,
                "provider_display_name": llm_manager.get_provider_display_name(provider)
            }
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in chat_with_agent: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def formatAgentName(agent: str) -> str:
    """Format agent name for display"""
    import re
    parts = re.findall(r'[A-Z][a-z]*', agent)
    return " ".join(parts).title() if parts else agent.title()

def format_tasks(tasks: List[Dict[str, Any]]) -> str:
    """Format tasks for display in the prompt"""
    if not tasks:
        return "You have no assigned tasks for this project yet."
    
    formatted = []
    for task in tasks:
        status = task.get("status", "pending").upper()
        formatted.append(f"- {task.get('name', 'Unnamed task')} ({status})\n  {task.get('description', 'No description')}")
    
    return "\n".join(formatted)

@app.get("/api/conversations/{agent}")
async def get_conversations(agent: str, project: str | None = None):
    try:
        agent_instance = agents.get(agent)
        if not agent_instance:
            raise HTTPException(status_code=404, detail=f"Agent {agent} not found")
        
        try:
            conversations = agent_instance.get_conversations()
            # Filter conversations by project if provided
            if project:
                conversations = [conv for conv in conversations if conv.get("project") == project]
            return {"conversations": conversations}
        except AttributeError:
            print(f"Warning: Agent {agent} doesn't have get_conversations method")
            return {"conversations": []}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in get_conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# Define API endpoints for LLM model management
@app.get("/api/llm/providers")
async def get_llm_providers():
    """Get all available LLM providers."""
    try:
        providers = llm_manager.get_available_providers()
        display_names = {p: llm_manager.get_provider_display_name(p) for p in providers}
        return {
            "status": "success", 
            "providers": providers,
            "display_names": display_names,
            "current_provider": llm_manager.get_current_provider()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/llm/models/{provider}")
async def get_llm_models(provider: str):
    """Get available models for the specified provider."""
    try:
        if provider not in llm_manager.get_available_providers():
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
        
        models = llm_manager.get_available_models(provider)
        return {
            "status": "success", 
            "models": models,
            "current_model": llm_manager.get_current_model(provider)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/provider")
async def set_llm_provider(request: LLMProviderRequest):
    """Set the current LLM provider."""
    try:
        if request.provider not in llm_manager.get_available_providers():
            raise HTTPException(status_code=404, detail=f"Provider {request.provider} not found")
        
        success = llm_manager.set_provider(request.provider)
        if not success:
            raise HTTPException(status_code=400, detail=f"Failed to set provider {request.provider}")
        
        return {
            "status": "success", 
            "provider": request.provider,
            "model": llm_manager.get_current_model(request.provider)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/model")
async def set_llm_model(request: LLMModelRequest):
    """Set the current model for a specific provider."""
    try:
        if request.provider not in llm_manager.get_available_providers():
            raise HTTPException(status_code=404, detail=f"Provider {request.provider} not found")
        
        available_models = llm_manager.get_available_models(request.provider)
        if request.model not in available_models:
            raise HTTPException(
                status_code=404, 
                detail=f"Model {request.model} not found for provider {request.provider}. Available models: {available_models}"
            )
        
        success = llm_manager.set_model(request.provider, request.model)
        if not success:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to set model {request.model} for provider {request.provider}"
            )
        
        return {
            "status": "success", 
            "provider": request.provider,
            "model": request.model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 AI Avatar Team Execution Started!")
    uvicorn.run(app, host="0.0.0.0", port=8000)
