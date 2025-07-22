import sys
import os
import asyncio
import zipfile
import tempfile
import re
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
from utils.database import connect_to_mongodb, close_mongodb_connection, create_project as db_create_project, list_projects as db_list_projects, get_project as db_get_project, get_project_tasks, plan_project as db_plan_project, update_task_status, create_team_member_name, get_team_member_name, get_all_team_member_names, delete_team_member_name
from utils.helpers import serialize_model
from memory.mongo_memory import mongo_shared_memory

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

# Register all agents with the ProductManager (team lead)
agents["productManager"].register_agents(agents)

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

# Add new request models for project and agent coordination
class ProjectRequestBreakdown(BaseModel):
    request: str
    
class A2ACommunicationRequest(BaseModel):
    target_agent: str
    message: str
    
class MCPTaskRequest(BaseModel):
    task: str
    agents: List[str]

# Add new request models for LLM settings
class LLMProviderRequest(BaseModel):
    provider: str

class LLMModelRequest(BaseModel):
    provider: str
    model: str

class TaskAssignmentRequest(BaseModel):
    agent: str
    task: str

# Add new request models for project planning
class ProjectPlanRequest(BaseModel):
    project_name: str
    project_description: str

class DiscussPlanRequest(BaseModel):
    project_name: str
    plan_summary: str

class FinalizePlanRequest(BaseModel):
    project_name: str
    client_approval: bool = False

# Add new request models for team member names
class TeamMemberNameRequest(BaseModel):
    role: str
    name: str

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

# Add default team member names if not existing
async def initialize_default_team_names():
    """Initialize default team member names if they don't exist"""
    default_names = {
        "chiefArchitect": "Chief Architect",
        "frontendEngineer": "Frontend Engineer",
        "backendEngineer": "Backend Engineer",
        "devopsEngineer": "DevOps Engineer",
        "aiMlEngineer": "AI/ML Engineer",
        "productManager": "Product Manager",
        "uiUxDesigner": "UI/UX Designer",
        "technicalWriter": "Technical Writer",
        "customerSuccess": "Customer Success",
        "legalCompliance": "Legal Compliance",
        "marketingSales": "Marketing & Sales"
    }
    
    for role, name in default_names.items():
        try:
            existing = await get_team_member_name(role)
            if not existing:
                await create_team_member_name(role, name)
        except Exception as e:
            print(f"Error initializing name for {role}: {str(e)}")
            # Continue with other names even if one fails

# Startup event to initialize team names
@app.on_event("startup")
async def startup_init():
    try:
        app.mongodb = await connect_to_mongodb()
        await initialize_default_team_names()
        print("Successfully initialized team names")
    except Exception as e:
        print(f"Error during startup initialization: {str(e)}")
        # Don't raise the exception to allow the application to start anyway

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
        return {"status": "success", "tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# New API endpoints for ProductManager team lead functionality

@app.post("/api/project/breakdown")
async def breakdown_project_request(request: ProjectRequestBreakdown):
    """Break down any project request into subtasks for team members."""
    try:
        product_manager = agents["productManager"]
        breakdown = product_manager.breakdown_project_request(request.request)
        return {"status": "success", "breakdown": breakdown}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error breaking down project request: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/project/status")
async def get_project_status():
    """Get status report for the current project."""
    try:
        product_manager = agents["productManager"]
        status = product_manager.update_project_status()
        return {"status": "success", "project_status": status}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error getting project status: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/a2a/communicate")
async def agent_to_agent_communication(request: A2ACommunicationRequest):
    """Use A2A protocol for direct agent communication."""
    try:
        product_manager = agents["productManager"]
        
        # Get display names for more natural communication
        try:
            from_name = await get_agent_display_name("productManager")
            to_name = await get_agent_display_name(request.target_agent)
            
            # Add name context to the message
            message = f"This is {from_name} speaking to {to_name}: {request.message}"
        except:
            # Fall back to original message if naming fails
            message = request.message
        
        # This is async, we need to await it
        response = await product_manager.communicate_with_agent(request.target_agent, message)
        return {"status": "success", "response": response}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in A2A communication: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/coordinate")
async def coordinate_multi_agent_task(request: MCPTaskRequest):
    """Use MCP server to coordinate a task across multiple agents."""
    try:
        product_manager = agents["productManager"]
        # This is async, we need to await it
        results = await product_manager.coordinate_multi_agent_task(request.task, request.agents)
        return {"status": "success", "results": results}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in MCP coordination: {str(e)}\n{error_details}")
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
            try:
                # Set current project first
                project_manager.current_project = request.project
                
                # Get project details and agent-specific tasks
                project_data = await db_get_project(request.project)
                
                # Convert Project object to dictionary if needed
                if hasattr(project_data, 'dict'):
                    # If it's a Pydantic model with dict() method
                    project_context = project_data.dict()
                elif hasattr(project_data, '__dict__'):
                    # If it's a regular object with __dict__
                    project_context = project_data.__dict__
                else:
                    # Fallback to serialize it
                    project_context = serialize_model(project_data)
                
                agent_tasks = await get_project_tasks(request.project)
                agent_tasks = [task for task in agent_tasks if task.get("assigned_to") == request.agent]
            except Exception as e:
                print(f"Error getting project context: {str(e)}")
                import traceback
                print(traceback.format_exc())
                # Continue with empty context
                project_context = {}
        
        # Modify the agent to use the current LLM provider and model
        provider = llm_manager.get_current_provider()
        model = llm_manager.get_current_model(provider)
        
        # Get agent's custom name
        agent_name = await get_agent_display_name(request.agent)
        
        # Prepare context for the agent
        context = {
            "role": agent_obj.role,
            "goal": agent_obj.goal,
            "backstory": agent_obj.backstory,
            "display_name": agent_name
        }
        
        if request.project:
            context["current_project"] = request.project
            context["project_details"] = project_context
            context["my_tasks"] = agent_tasks
        
        # Create a prompt that includes project context if available
        prompt = request.message
        if request.project:
            project_description = project_context.get('description', 'No description available')
            if not isinstance(project_description, str):
                project_description = str(project_description)
                
            prompt = f"""
You are working on the project "{request.project}".
Project description: {project_description}

Your assigned tasks:
{format_tasks(agent_tasks)}

As {agent_name}, with your expertise and role, please respond to:
{request.message}
"""
        else:
            prompt = f"""
As {agent_name}, with your expertise and role, please respond to:
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
        
        # Also store in MongoDB for shared context
        try:
            # Don't use mongo_shared_memory in a boolean context
            # Just call the method directly
            await mongo_shared_memory.add_message(
                request.agent, 
                request.message, 
                response,
                request.project
            )
        except Exception as e:
            print(f"Error storing conversation in MongoDB: {str(e)}")
        
        return {
            "status": "success", 
            "response": response,
            "agent": request.agent,
            "agent_display_name": agent_name,
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
    """Format agent name for display, checking for custom names first"""
    try:
        # We can't use async function directly here, so we'll use the default name generation
        parts = re.findall(r'[A-Z][a-z]*', agent)
        return " ".join(parts).title() if parts else agent.title()
    except Exception as e:
        print(f"Error formatting agent name: {str(e)}")
        return agent.title()

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

# Add API endpoints for project planning
@app.post("/api/project/plan/create")
async def create_project_plan(request: ProjectPlanRequest):
    """Create a comprehensive project plan for a new or existing project."""
    try:
        product_manager = agents["productManager"]
        plan = await product_manager.create_project_plan(request.project_name, request.project_description)
        return {"status": "success", "plan": plan}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating project plan: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/project/plan/discuss")
async def discuss_plan_with_team(request: DiscussPlanRequest):
    """Discuss the project plan with all team members to get their input."""
    try:
        product_manager = agents["productManager"]
        responses = await product_manager.discuss_plan_with_team(request.project_name, request.plan_summary)
        return {"status": "success", "responses": responses}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error discussing plan with team: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/project/plan/finalize")
async def finalize_project_plan(request: FinalizePlanRequest):
    """Finalize the project plan after team discussion and client approval."""
    try:
        product_manager = agents["productManager"]
        finalized_plan = await product_manager.finalize_project_plan(request.project_name, request.client_approval)
        return {"status": "success", "plan": finalized_plan}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error finalizing project plan: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

# API Endpoints for Team Member Names
@app.get("/api/team-names")
async def get_team_names():
    """Get all team member names."""
    try:
        names = await get_all_team_member_names()
        return {"status": "success", "names": names}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error getting team names: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/team-names/{role}")
async def get_team_name(role: str):
    """Get a team member's name by role."""
    try:
        name = await get_team_member_name(role)
        if not name:
            raise HTTPException(status_code=404, detail=f"No name found for role: {role}")
        return {"status": "success", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error getting team name: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/team-names")
async def set_team_name(request: TeamMemberNameRequest):
    """Set a team member's name."""
    try:
        # Validate role exists
        if request.role not in agents:
            raise HTTPException(status_code=404, detail=f"Agent role not found: {request.role}")
        
        result = await create_team_member_name(request.role, request.name)
        return {"status": "success", "name": result}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error setting team name: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/team-names/{role}")
async def remove_team_name(role: str):
    """Remove a team member's custom name."""
    try:
        # Validate role exists
        if role not in agents:
            raise HTTPException(status_code=404, detail=f"Agent role not found: {role}")
        
        success = await delete_team_member_name(role)
        if not success:
            raise HTTPException(status_code=404, detail=f"No custom name found for role: {role}")
        
        # Reset to default name
        default_name = formatAgentName(role)
        await create_team_member_name(role, default_name)
        
        return {"status": "success", "message": f"Custom name for {role} has been reset to default: {default_name}"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error removing team name: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e))

# Add a helper function to get agent display name (async version)
async def get_agent_display_name(agent: str) -> str:
    """Get the display name for an agent, using custom name if available"""
    try:
        custom_name = await get_team_member_name(agent)
        if custom_name and "name" in custom_name:
            return custom_name["name"]
        else:
            return formatAgentName(agent)
    except Exception as e:
        print(f"Error getting agent display name: {str(e)}")
        return formatAgentName(agent)

if __name__ == "__main__":
    print("🚀 AI Avatar Team Execution Started!")
    uvicorn.run(app, host="0.0.0.0", port=8000)
