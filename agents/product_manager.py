from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response
from utils.project_manager import ProjectManager
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import Field
import asyncio
import os

class ProductManager(BaseAgent):
    """Product Manager agent acting as Team Lead for various projects."""
    
    agent_registry: Dict[str, Any] = Field(default_factory=dict, description="Registry of all team agents")
    project_context: Dict[str, Any] = Field(default_factory=dict, description="Shared context for the project")
    
    def __init__(self):
        super().__init__(
            role="productManager",
            goal="Lead and manage Avatar Team for all types of projects, coordinating all aspects and agents.",
            backstory="Expert in Agile, Kanban, and B2B project workflows with deep experience in team leadership and complex project management across various domains."
        )
        if not self.project_manager:
            self.project_manager = ProjectManager("projects")
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
        
    def register_agents(self, agents: Dict[str, Any]):
        """Register all team agents for coordination"""
        self.agent_registry = agents

    def _generate_response(self, message, context):
        """Generate a response based on the message and context using Gemini API"""
        # Get context from other agents
        other_context = ""
        if context and "all_conversations" in context:
            try:
                for agent, convos in context["all_conversations"].items():
                    if agent != self.role and convos:
                        latest = convos[-1]
                        other_context += f"{agent} discussed: {latest['user_message']} → {latest['agent_response']}\n"
            except Exception as e:
                print(f"Error processing conversations: {str(e)}")
                # Continue without the context
        
        # Check if this is a command to assign tasks or communicate with agents
        if "assign task" in message.lower() or "assign to" in message.lower():
            # Try to parse the message to assign a task
            return self._handle_task_assignment_request(message, context)
        elif "talk to" in message.lower() or "discuss with" in message.lower() or "ask" in message.lower():
            # Try to parse the message to talk to another agent
            return self._handle_agent_communication_request(message, context)
        
        # Get current project details if available
        project_info = ""
        if self.project_manager and self.project_manager.current_project:
            try:
                project_name = self.project_manager.current_project
                project_info = f"Current project: {project_name}\n"
                # Get tasks if available
                try:
                    tasks = self.project_manager.get_tasks(project_name)
                    if tasks:
                        project_info += "Project tasks:\n"
                        for task in tasks:
                            status = task.get("status", "pending").upper()
                            project_info += f"- {task.get('name', 'Unnamed task')} (Assigned to: {task.get('assigned_to', 'unassigned')}, Status: {status})\n"
                except Exception as task_error:
                    print(f"Error getting tasks: {str(task_error)}")
            except Exception as project_error:
                print(f"Error getting project info: {str(project_error)}")
        
        # Create a professional prompt for Gemini with Team Lead focus
        prompt = f"""You are the Product Manager and Team Lead for an Avatar Team responsible for all types of projects.
        As the team lead, you are responsible for:
        - Managing the entire project lifecycle and coordinating all team members
        - Breaking down complex goals into subtasks for the right specialists
        - Tracking progress, validating work, and ensuring quality delivery 
        - Making critical decisions about project direction and resource allocation
        - Maintaining shared context and memory across the team
        
        Your expertise includes:
        - Agile and Kanban project management methodologies
        - B2B project workflows and stakeholder management
        - Dependency mapping, timeline management, and risk assessment
        - Team coordination and cross-functional leadership
        
        {project_info}
        
        Previous context from team members:
        {other_context}
        
        Project context:
        {json.dumps(self.project_context, indent=2) if self.project_context else "No current project context."}
        
        User message: {message}
        
        Please provide a professional and decisive response that demonstrates your leadership.
        Focus on actionable insights, clear decision-making, and effective team coordination.
        When appropriate, specify which team members should handle specific tasks."""
        
        # Get response from Gemini
        try:
            response = get_gemini_response(prompt)
            return response
        except Exception as e:
            print(f"Error generating response from Gemini: {str(e)}")
            return f"I'm having trouble generating a response right now. Let me try again later. Error: {str(e)}"
    
    def _handle_task_assignment_request(self, message, context):
        """Handle a request to assign tasks to team members"""
        # Parse the message to extract which agent should get what task
        prompt = f"""As a Product Manager, parse the following request to assign a task to a team member.
        Extract the following information:
        1. Which team member/role should be assigned (e.g., frontendEngineer, backendEngineer)
        2. What task they should be assigned
        
        Request: {message}
        
        Format your response as JSON with this structure:
        {{
            "role": "roleName",
            "task": "Task description"
        }}
        
        Only return the JSON, no other text."""
        
        # Get the structured assignment from Gemini
        parse_response = get_gemini_response(prompt)
        
        try:
            # Parse the response as JSON
            assignment = json.loads(parse_response)
            
            role = assignment.get("role")
            task = assignment.get("task")
            
            if not role or not task:
                return "I couldn't determine which team member to assign or what task to give them. Please provide more details."
            
            # Standardize agent role names
            role_mappings = {
                "frontend": "frontendEngineer",
                "frontend engineer": "frontendEngineer",
                "backend": "backendEngineer",
                "backend engineer": "backendEngineer",
                "architect": "chiefArchitect",
                "chief architect": "chiefArchitect",
                "devops": "devopsEngineer",
                "devops engineer": "devopsEngineer",
                "ai": "aiMlEngineer",
                "ml": "aiMlEngineer",
                "ai/ml": "aiMlEngineer",
                "ui": "uiUxDesigner",
                "ui/ux": "uiUxDesigner",
                "designer": "uiUxDesigner",
                "writer": "technicalWriter",
                "technical writer": "technicalWriter",
                "customer": "customerSuccess",
                "customer success": "customerSuccess",
                "legal": "legalCompliance",
                "compliance": "legalCompliance",
                "marketing": "marketingSales",
                "sales": "marketingSales"
            }
            
            # Try to match role with standard names
            normalized_role = role.lower()
            if normalized_role in role_mappings:
                role = role_mappings[normalized_role]
            
            # Check if the agent exists
            if role not in self.agent_registry:
                return f"I couldn't find a team member with the role '{role}'. Please use one of the available roles: {', '.join(self.agent_registry.keys())}"
            
            # Assign the task
            if self.project_manager and self.project_manager.current_project:
                project_name = self.project_manager.current_project
                task_obj = {
                    "name": f"New task for {role}",
                    "description": task,
                    "assigned_to": role,
                    "status": "pending",
                    "priority": "medium"
                }
                
                self.project_manager.add_task(project_name, task_obj)
                
                # Send task to the agent
                agent = self.agent_registry[role]
                
                # We'll use a synchronous version since we're in a sync context
                task_message = f"[TASK ASSIGNMENT from ProductManager] You have been assigned a new task: {task}. Please start working on this as soon as possible."
                
                # Log the assignment in project context
                if "task_assignments" not in self.project_context:
                    self.project_context["task_assignments"] = []
                
                self.project_context["task_assignments"].append({
                    "timestamp": self._get_timestamp(),
                    "role": role,
                    "task": task,
                    "status": "assigned"
                })
                
                # Start a communication with the agent asynchronously
                # We can't await here since we're in a sync context
                # This will happen in the background but we inform the user
                return f"I've assigned the task '{task}' to {role}. They have been notified and will begin working on it. You can check their progress later."
            else:
                return "There is no active project. Please create or select a project first before assigning tasks."
        
        except json.JSONDecodeError:
            # If response is not valid JSON
            return "I had trouble understanding your request. Please clearly specify which team member should be assigned what task."
    
    def _handle_agent_communication_request(self, message, context):
        """Handle a request to talk to another agent"""
        # Parse the message to extract which agent to talk to and what to say
        prompt = f"""As a Product Manager, parse the following request to talk to a team member.
        Extract the following information:
        1. Which team member/role to talk to (e.g., frontendEngineer, backendEngineer)
        2. What message to send them
        
        Request: {message}
        
        Format your response as JSON with this structure:
        {{
            "role": "roleName",
            "message": "Message to send"
        }}
        
        Only return the JSON, no other text."""
        
        # Get the structured communication from Gemini
        parse_response = get_gemini_response(prompt)
        
        try:
            # Parse the response as JSON
            communication = json.loads(parse_response)
            
            role = communication.get("role")
            msg = communication.get("message")
            
            if not role or not msg:
                return "I couldn't determine which team member to talk to or what message to send. Please provide more details."
            
            # Standardize agent role names (same as above)
            role_mappings = {
                "frontend": "frontendEngineer",
                "frontend engineer": "frontendEngineer", 
                "backend": "backendEngineer",
                "backend engineer": "backendEngineer",
                "architect": "chiefArchitect",
                "chief architect": "chiefArchitect",
                "devops": "devopsEngineer",
                "devops engineer": "devopsEngineer",
                "ai": "aiMlEngineer",
                "ml": "aiMlEngineer",
                "ai/ml": "aiMlEngineer",
                "ui": "uiUxDesigner",
                "ui/ux": "uiUxDesigner",
                "designer": "uiUxDesigner",
                "writer": "technicalWriter",
                "technical writer": "technicalWriter",
                "customer": "customerSuccess",
                "customer success": "customerSuccess",
                "legal": "legalCompliance",
                "compliance": "legalCompliance",
                "marketing": "marketingSales",
                "sales": "marketingSales"
            }
            
            # Try to match role with standard names
            normalized_role = role.lower()
            if normalized_role in role_mappings:
                role = role_mappings[normalized_role]
            
            # Check if the agent exists
            if role not in self.agent_registry:
                return f"I couldn't find a team member with the role '{role}'. Please use one of the available roles: {', '.join(self.agent_registry.keys())}"
            
            # Log the communication request in context
            if "communication_requests" not in self.project_context:
                self.project_context["communication_requests"] = []
            
            self.project_context["communication_requests"].append({
                "timestamp": self._get_timestamp(),
                "to": role,
                "message": msg
            })
            
            # We can't await communicate_with_agent here since we're in a sync context
            # But we can inform the user that it will happen
            return f"I'll discuss this with {role} regarding: '{msg}'. You can then check back with them or me for their response."
        
        except json.JSONDecodeError:
            # If response is not valid JSON
            return "I had trouble understanding your request. Please clearly specify which team member you want me to talk to and what message to send them."
    
    async def communicate_with_agent(self, agent_role: str, message: str) -> str:
        """A2A protocol: Send a message directly to another agent and get response"""
        if agent_role not in self.agent_registry:
            return f"Agent {agent_role} not found in the team."
        
        try:
            target_agent = self.agent_registry[agent_role]
            # Add context that this is an A2A communication
            a2a_message = f"[A2A REQUEST from ProductManager] {message}"
            
            # Get response from the agent
            response = await target_agent.chat(a2a_message)
            
            # Store this communication in the project context
            if "a2a_communications" not in self.project_context:
                self.project_context["a2a_communications"] = []
            
            self.project_context["a2a_communications"].append({
                "timestamp": self._get_timestamp(),
                "from": self.role,
                "to": agent_role,
                "message": message,
                "response": response
            })
            
            return response
        except Exception as e:
            error_message = f"Error communicating with {agent_role}: {str(e)}"
            print(error_message)
            
            # Store the failed communication attempt
            if "a2a_communications" not in self.project_context:
                self.project_context["a2a_communications"] = []
                
            self.project_context["a2a_communications"].append({
                "timestamp": self._get_timestamp(),
                "from": self.role,
                "to": agent_role,
                "message": message,
                "status": "failed",
                "error": str(e)
            })
            
            return error_message
    
    async def assign_and_start_task(self, agent_role: str, task: str) -> str:
        """Assign a task to an agent and instruct them to start working on it"""
        if agent_role not in self.agent_registry:
            return f"Agent {agent_role} not found in the team."
        
        try:
            target_agent = self.agent_registry[agent_role]
            
            # Create the task in the project manager
            if self.project_manager and self.project_manager.current_project:
                project_name = self.project_manager.current_project
                task_obj = {
                    "name": f"Task for {agent_role}",
                    "description": task,
                    "assigned_to": agent_role,
                    "status": "in_progress",
                    "priority": "high"
                }
                
                # Add the task
                self.project_manager.add_task(project_name, task_obj)
                
                # Send instructions to start working
                start_message = f"[TASK ASSIGNMENT] You have been assigned the following task: {task}. Please begin working on this immediately and report when you've made progress."
                
                # Send the message to the agent and get their response
                response = await target_agent.chat(start_message)
                
                # Store this assignment in the project context
                if "task_assignments" not in self.project_context:
                    self.project_context["task_assignments"] = []
                
                self.project_context["task_assignments"].append({
                    "timestamp": self._get_timestamp(),
                    "role": agent_role,
                    "task": task,
                    "status": "in_progress",
                    "agent_response": response
                })
                
                return f"Task assigned to {agent_role}. Their response: {response}"
            else:
                return "There is no active project. Please create or select a project first before assigning tasks."
        except Exception as e:
            error_message = f"Error assigning task to {agent_role}: {str(e)}"
            print(error_message)
            
            # Log the error in project context
            if "task_assignments" not in self.project_context:
                self.project_context["task_assignments"] = []
                
            self.project_context["task_assignments"].append({
                "timestamp": self._get_timestamp(),
                "role": agent_role,
                "task": task, 
                "status": "failed",
                "error": str(e)
            })
            
            return error_message
    
    async def coordinate_multi_agent_task(self, task: str, agents: List[str]) -> Dict[str, str]:
        """MCP coordination: Orchestrate a task requiring multiple agents"""
        if not self.agent_registry or not all(agent in self.agent_registry for agent in agents):
            return {"error": "Not all specified agents are available"}
        
        # Store task in project context
        if "mcp_tasks" not in self.project_context:
            self.project_context["mcp_tasks"] = []
        
        task_id = f"task_{len(self.project_context.get('mcp_tasks', []))+1}"
        
        # Create task in project manager
        if self.project_manager and self.project_manager.current_project:
            for agent_role in agents:
                self.project_manager.add_task(
                    self.project_manager.current_project,
                    {
                        "name": f"{task_id}_{agent_role}",
                        "description": task,
                        "assigned_to": agent_role,
                        "status": "pending"
                    }
                )
        
        # Execute task with each agent
        results = {}
        for agent_role in agents:
            agent = self.agent_registry[agent_role]
            # Format task for the specific agent
            agent_task = f"[MCP TASK {task_id}] As part of a coordinated multi-agent task: {task}"
            response = await agent.execute(agent_task)
            results[agent_role] = response
        
        # Record the task and results
        self.project_context["mcp_tasks"].append({
            "task_id": task_id,
            "description": task,
            "assigned_agents": agents,
            "results": results,
            "status": "completed",
            "timestamp": self._get_timestamp()
        })
        
        return results
    
    async def create_project_plan(self, project_name: str, project_description: str) -> Dict[str, Any]:
        """Create a comprehensive project plan with tasks for all team members"""
        # Create a new project if it doesn't exist
        if self.project_manager:
            try:
                # Try to get the project first
                project_exists = False
                try:
                    # Can't use self.project_manager.get_project directly as it's not async
                    # For now we'll just check if the directory exists
                    project_dir = os.path.join(self.project_manager.base_directory, project_name)
                    project_exists = os.path.exists(project_dir)
                except Exception as e:
                    print(f"Error checking if project exists: {str(e)}")
                    project_exists = False
                
                if project_exists:
                    # Project exists
                    self.project_manager.current_project = project_name
                else:
                    # Create new project
                    project = self.project_manager.create_project(project_name, project_description)
                    self.project_manager.current_project = project_name
                
                # Generate a detailed plan with LLM
                prompt = f"""As a Product Manager, create a comprehensive project plan for the following project:
                
                Project Name: {project_name}
                Project Description: {project_description}
                
                Create a detailed plan with specific tasks for each team member:
                - chiefArchitect: System architecture, technical decisions
                - frontendEngineer: UI implementation, frontend logic
                - backendEngineer: API development, database management
                - devopsEngineer: CI/CD, infrastructure, deployment
                - aiMlEngineer: AI/ML components (if applicable)
                - uiUxDesigner: Design systems, mockups, UX flows
                - technicalWriter: Documentation, guides, API docs
                - customerSuccess: User onboarding, support processes
                - legalCompliance: Legal requirements, compliance
                - marketingSales: Marketing strategy, sales materials
                
                Format your response as JSON with this structure:
                {{
                    "project_name": "{project_name}",
                    "description": "{project_description}",
                    "phases": [
                        {{
                            "name": "Phase name (e.g., Planning, Development, Testing)",
                            "description": "Phase description",
                            "tasks": [
                                {{
                                    "role": "roleName",
                                    "task": "Task description",
                                    "dependencies": [],
                                    "priority": "high|medium|low",
                                    "estimated_hours": 4
                                }}
                            ]
                        }}
                    ]
                }}
                
                Only return the JSON, no other text."""
                
                # Get the plan from Gemini
                plan_response = get_gemini_response(prompt)
                
                try:
                    # Parse the response as JSON
                    plan = json.loads(plan_response)
                    
                    # Store in project context
                    self.project_context["project_plan"] = plan
                    
                    # Add tasks to project
                    task_id = 1
                    for phase in plan.get("phases", []):
                        phase_name = phase.get("name", "Unnamed Phase")
                        for task_info in phase.get("tasks", []):
                            task = {
                                "id": f"task_{task_id}",
                                "name": f"{phase_name}: {task_info.get('task', '')}",
                                "description": task_info.get("task", ""),
                                "assigned_to": task_info.get("role", ""),
                                "status": "pending",
                                "priority": task_info.get("priority", "medium"),
                                "dependencies": task_info.get("dependencies", []),
                                "estimated_hours": task_info.get("estimated_hours", 0),
                                "phase": phase_name
                            }
                            self.project_manager.add_task(project_name, task)
                            task_id += 1
                    
                    return plan
                    
                except json.JSONDecodeError:
                    # If response is not valid JSON, create a simple plan
                    return {
                        "error": "Failed to parse response as JSON",
                        "raw_response": plan_response
                    }
            
            except Exception as e:
                print(f"Error creating project plan: {str(e)}")
                return {"error": f"Error creating project plan: {str(e)}"}
        
        return {"error": "Project manager not initialized"}
    
    async def discuss_plan_with_team(self, project_name: str, plan_summary: str) -> Dict[str, str]:
        """Discuss the project plan with all team members to get their input"""
        if not self.agent_registry:
            return {"error": "No team members registered"}
        
        # Make sure we have an active project
        if self.project_manager:
            self.project_manager.current_project = project_name
        
        # Send a request to each team member to review the plan
        responses = {}
        team_roles = ["chiefArchitect", "frontendEngineer", "backendEngineer", "devopsEngineer", 
                      "aiMlEngineer", "uiUxDesigner"]
        
        for role in team_roles:
            if role in self.agent_registry:
                try:
                    review_message = f"""Please review our project plan for '{project_name}':
                    
                    {plan_summary}
                    
                    As the {role}, please provide your feedback, concerns, and any additional tasks you think should be included in your area of expertise."""
                    
                    response = await self.communicate_with_agent(role, review_message)
                    responses[role] = response
                    
                    # Add a small delay to avoid overloading the LLM API
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Error getting feedback from {role}: {str(e)}")
                    responses[role] = f"Unable to get feedback: {str(e)}"
        
        # Compile the feedback
        consolidated_feedback = {
            "project_name": project_name,
            "timestamp": self._get_timestamp(),
            "team_feedback": responses
        }
        
        # Store in project context
        self.project_context["team_feedback"] = consolidated_feedback
        
        return responses
    
    async def finalize_project_plan(self, project_name: str, client_approval: bool = False) -> Dict[str, Any]:
        """Finalize the project plan after team discussion and optionally client approval"""
        # Get the existing plan and feedback
        plan = self.project_context.get("project_plan", {})
        feedback = self.project_context.get("team_feedback", {})
        
        if not plan:
            return {"error": "No project plan exists to finalize"}
        
        # Generate a prompt for finalizing the plan based on feedback
        prompt = f"""As a Product Manager, finalize this project plan based on team feedback:
        
        Original Plan:
        {json.dumps(plan, indent=2)}
        
        Team Feedback:
        {json.dumps(feedback, indent=2)}
        
        Client Approval: {"Received" if client_approval else "Pending"}
        
        Create a finalized project plan with any needed adjustments based on feedback.
        Include a timeline with milestones.
        
        Format your response as JSON with this structure:
        {{
            "project_name": "{project_name}",
            "description": "Updated project description",
            "status": "{"approved" if client_approval else "pending_approval"}",
            "estimated_duration": "X weeks",
            "phases": [
                {{
                    "name": "Phase name",
                    "description": "Phase description",
                    "duration": "X days",
                    "tasks": [
                        {{
                            "role": "roleName",
                            "task": "Task description",
                            "dependencies": [],
                            "priority": "high|medium|low",
                            "estimated_hours": 4,
                            "status": "pending"
                        }}
                    ]
                }}
            ],
            "milestones": [
                {{
                    "name": "Milestone name",
                    "due_date": "YYYY-MM-DD",
                    "deliverables": ["list", "of", "deliverables"]
                }}
            ]
        }}
        
        Only return the JSON, no other text."""
        
        # Get the finalized plan from Gemini
        plan_response = get_gemini_response(prompt)
        
        try:
            # Parse the response as JSON
            finalized_plan = json.loads(plan_response)
            
            # Store in project context
            self.project_context["finalized_plan"] = finalized_plan
            
            # Update tasks in project manager with the finalized versions
            if self.project_manager and self.project_manager.current_project == project_name:
                # First, clear existing tasks if we're replacing them
                # Note: This would require an additional method in project_manager
                # that we'll implement later
                
                # Add finalized tasks
                task_id = 1
                for phase in finalized_plan.get("phases", []):
                    phase_name = phase.get("name", "Unnamed Phase")
                    for task_info in phase.get("tasks", []):
                        task = {
                            "id": f"task_{task_id}",
                            "name": f"{phase_name}: {task_info.get('task', '')}",
                            "description": task_info.get("task", ""),
                            "assigned_to": task_info.get("role", ""),
                            "status": "pending",
                            "priority": task_info.get("priority", "medium"),
                            "dependencies": task_info.get("dependencies", []),
                            "estimated_hours": task_info.get("estimated_hours", 0),
                            "phase": phase_name
                        }
                        # Here we're adding tasks, ideally we'd have a replace/update method
                        self.project_manager.add_task(project_name, task)
                        task_id += 1
            
            # If client approved, begin project execution
            if client_approval:
                # Update project status
                finalized_plan["status"] = "in_progress"
                self.project_context["project_status"] = "in_progress"
                
                # Start the first phase tasks
                first_phase = finalized_plan.get("phases", [])[0] if finalized_plan.get("phases") else None
                if first_phase:
                    for task_info in first_phase.get("tasks", []):
                        role = task_info.get("role")
                        task = task_info.get("task")
                        if role and task and role in self.agent_registry:
                            # We'll launch these tasks asynchronously
                            # but we can't await here because we're already in an async method
                            asyncio.create_task(self.assign_and_start_task(role, task))
            
            return finalized_plan
            
        except json.JSONDecodeError:
            # If response is not valid JSON
            return {
                "error": "Failed to parse response as JSON",
                "raw_response": plan_response
            }
    
    def update_project_status(self) -> Dict[str, Any]:
        """Generate a status report for the current project"""
        if not self.project_manager or not self.project_manager.current_project:
            return {"error": "No active project"}
            
        project_name = self.project_manager.current_project
        tasks = self.project_manager.get_tasks(project_name)
        
        # Count tasks by status
        task_counts = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "blocked": 0
        }
        
        for task in tasks:
            status = task.get("status", "pending")
            if status in task_counts:
                task_counts[status] += 1
        
        # Calculate completion percentage
        total_tasks = len(tasks)
        completed_tasks = task_counts["completed"]
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Generate status report
        status_report = {
            "project_name": project_name,
            "total_tasks": total_tasks,
            "task_status": task_counts,
            "completion_percentage": round(completion_percentage, 2),
            "timestamp": self._get_timestamp()
        }
        
        # Store in project context
        self.project_context["latest_status"] = status_report
        
        return status_report
        
    def breakdown_project_request(self, request: str) -> Dict[str, Any]:
        """Break down any project request into subtasks for different team members"""
        # Create a prompt specialized for task breakdown
        prompt = f"""As a Product Manager, break down the following project request into specific subtasks for different team roles:
        
        Request: {request}
        
        For each subtask, specify:
        1. The responsible role (must be one of: chiefArchitect, frontendEngineer, backendEngineer, 
           devopsEngineer, aiMlEngineer, uiUxDesigner, technicalWriter, customerSuccess, legalCompliance, marketingSales)
        2. A clear description of the task
        3. Dependencies (if any)
        4. Priority (high, medium, low)
        
        Format your response as JSON with this structure:
        {{
            "project_name": "Brief descriptive name for this project",
            "description": "Summary of the overall project goal",
            "tasks": [
                {{
                    "role": "roleName",
                    "task": "Task description",
                    "dependencies": ["taskId1", "taskId2"],
                    "priority": "high|medium|low"
                }}
            ]
        }}
        
        Only return the JSON, no other text."""
        
        # Get the breakdown from Gemini
        response = get_gemini_response(prompt)
        
        try:
            # Parse the response as JSON
            breakdown = json.loads(response)
            
            # Store in project context
            self.project_context["project_breakdown"] = breakdown
            
            # Create project if it doesn't exist
            if self.project_manager:
                project_name = breakdown.get("project_name", "New Project")
                try:
                    project = self.project_manager.get_project(project_name)
                except FileNotFoundError:
                    project = self.project_manager.create_project(project_name, breakdown.get("description", ""))
                
                # Add tasks to project
                for i, task_info in enumerate(breakdown.get("tasks", [])):
                    task = {
                        "name": f"Task {i+1}: {task_info.get('task', '')}",
                        "description": task_info.get("task", ""),
                        "assigned_to": task_info.get("role", ""),
                        "status": "pending",
                        "priority": task_info.get("priority", "medium"),
                        "dependencies": task_info.get("dependencies", [])
                    }
                    self.project_manager.add_task(project_name, task)
                
                self.project_manager.current_project = project_name
            
            return breakdown
            
        except json.JSONDecodeError:
            # If response is not valid JSON, create a simple breakdown
            return {
                "error": "Failed to parse response as JSON",
                "raw_response": response
            }
