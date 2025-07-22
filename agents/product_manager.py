from agents.base_agent import BaseAgent
from config.gemini_config import get_gemini_response
from utils.project_manager import ProjectManager
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import Field
import asyncio
import os
import re

# Import function to get team member names
try:
    from utils.database import get_team_member_name
except ImportError:
    # Mock function for compatibility if database module doesn't have it
    async def get_team_member_name(role):
        return None

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
        # First check for command patterns - we'll bypass the LLM entirely for these
        msg_lower = message.lower()
        
        # Check for "contact team" or "get status" type commands
        # These are MUST MATCH patterns - we want to ensure the LLM doesn't generate 
        # email templates for these specific commands
        team_contact_patterns = [
            "contact your team", 
            "contact the team",
            "get status from team", 
            "get team status",
            "get updates from team",
            "team status update",
            "check with the team",
            "talk to your team",
            "ask the team for status"
        ]
        
        # Direct API call for team contact
        if any(pattern in msg_lower for pattern in team_contact_patterns):
            print("DETECTED TEAM CONTACT COMMAND - BYPASSING LLM")
            try:
                # For logging to verify this is being called
                print(f"🚀 Executing direct team contact for command: {message}")
                
                # Use API to contact all agents directly
                team_members = ["frontendEngineer", "backendEngineer", "chiefArchitect", "uiUxDesigner"]
                status_query = "What's your current status and what are you working on for this project? Please provide a brief update."
                
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                results = {}
                for agent in team_members:
                    if agent in self.agent_registry:
                        try:
                            print(f"📞 Directly contacting agent: {agent}")
                            # IMPORTANT: Using communicate_with_agent directly
                            response = loop.run_until_complete(
                                self.communicate_with_agent(agent, status_query)
                            )
                            results[agent] = response
                            print(f"✅ Got response from {agent}")
                        except Exception as e:
                            print(f"❌ Error contacting {agent}: {str(e)}")
                            results[agent] = f"Could not reach {agent}: {str(e)}"
                
                # Format the DIRECT results - not using LLM
                formatted_response = "## Team Status Report\n\nI've contacted the team members directly and received the following updates:\n\n"
                
                for agent, response in results.items():
                    formatted_response += f"### {agent}\n{response}\n\n"
                
                formatted_response += "\nI'll follow up with any team members who appear to be facing challenges or haven't made expected progress."
                
                print("✅ Successfully executed team contact command")
                return formatted_response
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ Error executing team contact: {str(e)}\n{error_details}")
                return f"⚠️ I tried to contact the team directly but encountered a technical error. Details: {str(e)}"
        
        # Team Task Assignment
        if "have the team" in msg_lower or "assign the team" in msg_lower or "get the team to" in msg_lower:
            print("DETECTED TEAM TASK ASSIGNMENT - BYPASSING LLM")
            try:
                # For logging
                print(f"🚀 Executing direct team task assignment: {message}")
                
                # Extract the task from the command
                task_parts = message.split("team")
                if len(task_parts) > 1:
                    task_description = task_parts[1].strip()
                else:
                    task_description = message
                
                # Use MCP API to coordinate multiple agents
                team_members = ["frontendEngineer", "backendEngineer", "chiefArchitect", "uiUxDesigner"]
                
                import asyncio
                
                async def run_coordination():
                    print("📊 Starting multi-agent coordination")
                    results = await self.coordinate_multi_agent_task(task_description, team_members)
                    print(f"✅ Completed coordination with results: {results.keys()}")
                    return results
                
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                results = loop.run_until_complete(run_coordination())
                
                # Format the direct results
                formatted_response = f"## Team Task Assignment: {task_description}\n\nI've assigned this task to the team and received the following responses:\n\n"
                
                for agent, response in results.items():
                    formatted_response += f"### {agent}\n{response}\n\n"
                
                formatted_response += "\nI'll track their progress and ensure the task is completed efficiently."
                
                print("✅ Successfully executed team task assignment")
                return formatted_response
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ Error executing team task assignment: {str(e)}\n{error_details}")
                return f"⚠️ I tried to assign the task to the team but encountered a technical error. Details: {str(e)}"
        
        # For individual tasks to specific team members
        # Try to detect patterns like "have X do Y" or "ask X to do Y"
        agent_task_patterns = [
            r"have (the )?([\w\s]+) (do|create|build|implement|design|work on) ([\w\s]+)",
            r"ask (the )?([\w\s]+) to (do|create|build|implement|design|work on) ([\w\s]+)",
            r"assign (the )?([\w\s]+) to (do|create|build|implement|design|work on) ([\w\s]+)"
        ]
        
        import re
        for pattern in agent_task_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                try:
                    # Extract agent and task
                    agent_role = match.group(2).strip()
                    task_verb = match.group(3).strip()
                    task_obj = match.group(4).strip()
                    
                    # Map common terms to agent role IDs
                    role_mapping = {
                        "frontend": "frontendEngineer",
                        "frontend engineer": "frontendEngineer",
                        "backend": "backendEngineer", 
                        "backend engineer": "backendEngineer",
                        "architect": "chiefArchitect",
                        "chief architect": "chiefArchitect",
                        "devops": "devopsEngineer",
                        "designer": "uiUxDesigner",
                        "ui designer": "uiUxDesigner",
                        "ux designer": "uiUxDesigner",
                        "ui/ux": "uiUxDesigner",
                        "ai": "aiMlEngineer",
                        "ml": "aiMlEngineer",
                        "ai engineer": "aiMlEngineer",
                        "writer": "technicalWriter",
                        "technical writer": "technicalWriter",
                        "customer": "customerSuccess",
                        "legal": "legalCompliance",
                        "marketing": "marketingSales"
                    }
                    
                    # Find the right agent
                    target_agent = None
                    for key, value in role_mapping.items():
                        if key in agent_role:
                            target_agent = value
                            break
                    
                    # If no match found, try direct match
                    if not target_agent and agent_role in self.agent_registry:
                        target_agent = agent_role
                    
                    if target_agent and target_agent in self.agent_registry:
                        # Execute the task assignment directly
                        print(f"🎯 Assigning task directly to {target_agent}: {task_verb} {task_obj}")
                        
                        task_description = f"{task_verb} {task_obj}"
                        
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # Call the assign_and_start_task method directly
                        response = loop.run_until_complete(self.assign_and_start_task(target_agent, task_description))
                        
                        return f"## Task Assignment\n\nI've assigned {target_agent} to {task_verb} {task_obj}. Here's their response:\n\n{response}"
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"❌ Error executing individual task assignment: {str(e)}\n{error_details}")
                    return f"⚠️ I tried to assign the task but encountered a technical error. Details: {str(e)}"
        
        # If none of the direct commands matched, use the normal LLM response
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
        
        # Detect project-related context automatically
        project_name = None
        if context and "current_project" in context:
            project_name = context["current_project"]
            # Update project manager's current project
            if self.project_manager:
                self.project_manager.current_project = project_name
        
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
        
        # Get the display name for the prompt
        display_name = context.get("display_name", "Product Manager")
        
        # Create a professional prompt for Gemini with Team Lead focus
        prompt = f"""You are {display_name}, the Product Manager and Team Lead for an Avatar Team responsible for all types of projects.
        Your name is {display_name}.
        
        EXTREMELY IMPORTANT: Do NOT generate template-like emails. Provide concise, direct responses that reflect actions you are taking right now.
        
        EXTREMELY IMPORTANT: When asked to contact team members or assign tasks, explain that you are doing this directly through the system API, not by sending emails.

        EXTREMELY IMPORTANT: You are the AI agent, but you must behave as if you are a human professional. You have your own team, and you interact directly with clients. Maintain a highly professional demeanor at all times.

        When a client gives you instructions, do not respond with phrases like "we need to schedule a meeting" or "we'll check client availability." Instead, you are expected to independently coordinate with your team (who are also AI agents acting like humans), discuss the task internally, and present a final plan to the client.
        
        If the client requests any changes to the plan, coordinate with your team again to revise it. Once the client approves the plan, immediately begin execution with your team. You are also responsible for collecting progress updates from every team member and keeping the client informed accordingly.
        
        Remember, your team consists of AI agents as well, but all of you must operate as if you're part of a real, professional human organization. 
        
        Current project information:
        {project_info}
        
        As the team lead, you are responsible for:
        - Managing the project lifecycle and coordinating team members
        - Breaking down goals into subtasks for specialists
        - Tracking progress and ensuring quality delivery
        - Making decisions about project direction
        
        Previous context from team members:
        {other_context}
        
        Project context:
        {json.dumps(self.project_context, indent=2) if self.project_context else "No current project context."}
        
        User message: {message}
        
        Provide direct, actionable responses. DO NOT create email templates or theoretical plans. Focus on real actions you're taking in the system."""
        
        # Get response from Gemini
        try:
            response = get_gemini_response(prompt)
            return response
        except Exception as e:
            print(f"Error generating response from Gemini: {str(e)}")
            return f"I'm having trouble generating a response right now. Let me try again later. Error: {str(e)}"
    
    def _handle_project_creation(self, message, project_name=None):
        """Handle project creation request"""
        if not project_name:
            # Extract project name from message
            project_name_match = re.search(r'project\s+(?:called|named)?\s*["\']?([A-Za-z0-9_-]+)["\']?', message)
            if project_name_match:
                project_name = project_name_match.group(1)
            else:
                project_name = "NewProject"
        
        # Extract project description from message
        description_match = re.search(r'for\s+(.*?)(?:\.|$)', message)
        description = description_match.group(1) if description_match else "New project"
        
        try:
            # Actually create the project
            if self.project_manager:
                project = self.project_manager.create_project(project_name, description)
                self.project_manager.current_project = project_name
                
                return f"I've created the project '{project_name}' with the description: '{description}'. The project has been initialized and is ready for planning. What specific aspects would you like me to focus on first?"
            else:
                return "I'm unable to create a project right now because the project manager is not available. Please check the system configuration."
        except Exception as e:
            return f"I tried to create the project but encountered an error: {str(e)}. Please check if the project already exists or if there's a system issue."
    
    def _handle_project_planning(self, message, project_name=None):
        """Handle project planning request"""
        if not self.project_manager or not self.project_manager.current_project and not project_name:
            return "I need an active project to create a plan. Please create or select a project first."
        
        project_name = project_name or self.project_manager.current_project
        
        try:
            # Create actual tasks for the project
            tasks = [
                {
                    "name": "Design system architecture",
                    "description": "Create a detailed system design document",
                    "assigned_to": "chiefArchitect",
                    "status": "pending",
                    "priority": "high"
                },
                {
                    "name": "Set up project repository",
                    "description": "Initialize git repository and project structure",
                    "assigned_to": "backendEngineer",
                    "status": "pending",
                    "priority": "high"
                },
                {
                    "name": "Create UI mockups",
                    "description": "Design user interface mockups for key screens",
                    "assigned_to": "uiUxDesigner",
                    "status": "pending",
                    "priority": "medium"
                },
                {
                    "name": "Set up CI/CD pipeline",
                    "description": "Configure continuous integration and deployment",
                    "assigned_to": "devopsEngineer",
                    "status": "pending",
                    "priority": "medium"
                }
            ]
            
            # Add tasks to the project
            for task in tasks:
                self.project_manager.add_task(project_name, task)
            
            # Extract key requirements from the message
            requirements = []
            if "social media" in message:
                requirements.append("social media platform")
            if "user profiles" in message:
                requirements.append("user profiles")
            if "posting" in message:
                requirements.append("posting capabilities")
            if "notification" in message:
                requirements.append("notification system")
            
            requirements_str = ", ".join(requirements) if requirements else "the application"
            
            return f"I've created a project plan for {project_name} with initial tasks assigned to the team. I've added tasks for the Chief Architect to design the system, Backend Engineer to set up the repository, UI/UX Designer to create mockups, and DevOps Engineer to set up CI/CD. These tasks focus on {requirements_str}. Would you like me to assign any additional specific tasks?"
        except Exception as e:
            return f"I tried to create a project plan but encountered an error: {str(e)}. Please check if the project exists and if the team members are available."
    
    def _handle_project_finalization(self, message, project_name=None):
        """Handle project finalization request"""
        if not self.project_manager or not self.project_manager.current_project and not project_name:
            return "I need an active project to finalize. Please create or select a project first."
        
        project_name = project_name or self.project_manager.current_project
        
        try:
            # Update task statuses to ready
            tasks = self.project_manager.get_tasks(project_name)
            for task in tasks:
                if task["status"] == "pending":
                    self.project_manager.update_task_status(project_name, task["id"], "ready")
            
            # Add a kickoff task
            kickoff_task = {
                "name": "Project Kickoff",
                "description": "Initial team meeting to align on project goals and tasks",
                "assigned_to": "productManager",
                "status": "in_progress",
                "priority": "high"
            }
            self.project_manager.add_task(project_name, kickoff_task)
            
            return f"I've finalized the project plan for {project_name}. All tasks are now marked as 'ready' and team members can begin work. I've scheduled a project kickoff to align the team on our goals. Each team member can view their assigned tasks. Is there anything specific you'd like me to focus on during the kickoff?"
        except Exception as e:
            return f"I tried to finalize the project plan but encountered an error: {str(e)}. Please check if the project exists and if there are any tasks created."
    
    def _handle_project_kickoff(self, message, project_name=None):
        """Handle project kickoff request"""
        if not self.project_manager or not self.project_manager.current_project and not project_name:
            return "I need an active project to kick off. Please create or select a project first."
        
        project_name = project_name or self.project_manager.current_project
        
        try:
            # Notify each team member about their tasks
            tasks_by_agent = {}
            all_tasks = self.project_manager.get_tasks(project_name)
            
            for task in all_tasks:
                agent_role = task.get("assigned_to")
                if agent_role and agent_role in self.agent_registry:
                    if agent_role not in tasks_by_agent:
                        tasks_by_agent[agent_role] = []
                    tasks_by_agent[agent_role].append(task)
            
            # Create notification messages
            for agent_role, tasks in tasks_by_agent.items():
                task_list = "\n".join([f"- {task['name']}: {task['description']} (Priority: {task.get('priority', 'medium')})" for task in tasks])
                notification = f"Project {project_name} has kicked off. You have been assigned the following tasks:\n\n{task_list}\n\nPlease begin work on these tasks in order of priority."
                
                # Store notification in project context
                if "kickoff_notifications" not in self.project_context:
                    self.project_context["kickoff_notifications"] = {}
                self.project_context["kickoff_notifications"][agent_role] = notification
            
            return f"I've kicked off the project {project_name}. All team members have been notified of their tasks and can begin work immediately. The Chief Architect will start with the system design, while the UI/UX Designer begins creating mockups. The Backend Engineer will set up the project repository, and the DevOps Engineer will prepare the CI/CD pipeline. I'll track progress and provide regular updates."
        except Exception as e:
            return f"I tried to kick off the project but encountered an error: {str(e)}. Please check if the project exists and if team members have been assigned tasks."
    
    def _handle_project_status(self, message, project_name=None):
        """Handle project status request"""
        if not self.project_manager or not self.project_manager.current_project and not project_name:
            return "I don't have an active project to provide status on. Please create or select a project first."
        
        project_name = project_name or self.project_manager.current_project
        
        try:
            # Get actual project tasks and their status
            tasks = self.project_manager.get_tasks(project_name)
            
            if not tasks:
                return f"Project {project_name} exists but doesn't have any tasks yet. Would you like me to create an initial project plan with tasks?"
            
            # Count tasks by status
            status_counts = {}
            for task in tasks:
                status = task.get("status", "pending")
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
            
            # Calculate completion percentage
            total_tasks = len(tasks)
            completed_tasks = status_counts.get("completed", 0)
            completion_percentage = int((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0)
            
            # Compile status by team member
            team_status = {}
            for task in tasks:
                assignee = task.get("assigned_to")
                if assignee:
                    if assignee not in team_status:
                        team_status[assignee] = {"total": 0, "completed": 0, "in_progress": 0, "pending": 0}
                    team_status[assignee]["total"] += 1
                    status = task.get("status", "pending")
                    if status in team_status[assignee]:
                        team_status[assignee][status] += 1
            
            # Format the response
            status_response = f"Current status of {project_name} (Overall completion: {completion_percentage}%):\n\n"
            
            # Add status breakdown
            status_response += "Task Status:\n"
            for status, count in status_counts.items():
                status_response += f"- {status.upper()}: {count} tasks\n"
            
            # Add team member breakdown
            status_response += "\nTeam Member Status:\n"
            for member, stats in team_status.items():
                try:
                    # Try to get display name
                    member_name = self.agent_registry[member].get_display_name() if member in self.agent_registry else member
                except:
                    member_name = member
                    
                member_completion = int((stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0)
                status_response += f"- {member_name}: {stats['completed']}/{stats['total']} tasks completed ({member_completion}%)\n"
            
            # Add next steps
            status_response += "\nNext Steps:\n"
            in_progress_tasks = [task for task in tasks if task.get("status") == "in_progress"]
            if in_progress_tasks:
                for task in in_progress_tasks[:3]:  # Show up to 3 in-progress tasks
                    assignee = task.get("assigned_to", "Unassigned")
                    status_response += f"- Continue work on '{task['name']}' (Assigned to: {assignee})\n"
            
            pending_tasks = [task for task in tasks if task.get("status") == "pending"]
            if pending_tasks:
                for task in pending_tasks[:3]:  # Show up to 3 pending tasks
                    assignee = task.get("assigned_to", "Unassigned")
                    status_response += f"- Start work on '{task['name']}' (Assigned to: {assignee})\n"
            
            return status_response
        except Exception as e:
            return f"I tried to get the project status but encountered an error: {str(e)}. Please check if the project exists and if there are any tasks created."
    
    def _handle_project_priorities(self, message, project_name=None):
        """Handle project priorities request"""
        if not self.project_manager or not self.project_manager.current_project and not project_name:
            return "I don't have an active project to provide priorities for. Please create or select a project first."
        
        project_name = project_name or self.project_manager.current_project
        
        try:
            # Get actual project tasks
            tasks = self.project_manager.get_tasks(project_name)
            
            if not tasks:
                return f"Project {project_name} exists but doesn't have any tasks yet. Would you like me to create an initial project plan with prioritized tasks?"
            
            # Filter tasks that aren't completed
            active_tasks = [task for task in tasks if task.get("status") != "completed"]
            
            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            active_tasks.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))
            
            # Format the response
            if not active_tasks:
                return f"All tasks in project {project_name} have been completed! Would you like me to create new tasks for the next phase?"
            
            # Group by priority
            priorities_response = f"Current priorities for {project_name}:\n\n"
            
            priorities_response += "HIGH PRIORITY:\n"
            high_priority = [task for task in active_tasks if task.get("priority") == "high"]
            if high_priority:
                for task in high_priority:
                    assignee = task.get("assigned_to", "Unassigned")
                    status = task.get("status", "pending").upper()
                    priorities_response += f"- {task['name']} (Assigned to: {assignee}, Status: {status})\n"
            else:
                priorities_response += "- No high priority tasks currently\n"
            
            priorities_response += "\nMEDIUM PRIORITY:\n"
            medium_priority = [task for task in active_tasks if task.get("priority") == "medium"]
            if medium_priority:
                for task in medium_priority[:3]:  # Show up to 3 medium priority tasks
                    assignee = task.get("assigned_to", "Unassigned")
                    status = task.get("status", "pending").upper()
                    priorities_response += f"- {task['name']} (Assigned to: {assignee}, Status: {status})\n"
                if len(medium_priority) > 3:
                    priorities_response += f"- Plus {len(medium_priority) - 3} more medium priority tasks\n"
            else:
                priorities_response += "- No medium priority tasks currently\n"
            
            priorities_response += "\nRecommended next actions:\n"
            pending_high = [task for task in high_priority if task.get("status") == "pending"]
            if pending_high:
                task = pending_high[0]
                assignee = task.get("assigned_to", "someone")
                priorities_response += f"1. {assignee} should start work on '{task['name']}'\n"
            
            blocked_tasks = [task for task in active_tasks if task.get("status") == "blocked"]
            if blocked_tasks:
                priorities_response += f"2. Address blockers for {len(blocked_tasks)} blocked tasks\n"
            
            return priorities_response
        except Exception as e:
            return f"I tried to determine project priorities but encountered an error: {str(e)}. Please check if the project exists and if there are any tasks created."
    
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
                "chief architect": "chiefArchitect",
                "architect": "chiefArchitect",
                "devops": "devopsEngineer",
                "devops engineer": "devopsEngineer",
                "ui": "uiUxDesigner",
                "ux": "uiUxDesigner",
                "designer": "uiUxDesigner",
                "ui ux": "uiUxDesigner",
                "ui ux designer": "uiUxDesigner",
                "ai": "aiMlEngineer",
                "ml": "aiMlEngineer",
                "ai ml": "aiMlEngineer",
                "ai ml engineer": "aiMlEngineer",
                "writer": "technicalWriter",
                "technical writer": "technicalWriter",
                "support": "customerSuccess",
                "customer success": "customerSuccess",
                "legal": "legalCompliance",
                "compliance": "legalCompliance",
                "legal compliance": "legalCompliance",
                "marketing": "marketingSales",
                "sales": "marketingSales",
                "marketing sales": "marketingSales"
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
        try:
            # Validate that the agent exists
            if agent_role not in self.agent_registry:
                valid_agents = list(self.agent_registry.keys())
                return f"Error: Agent '{agent_role}' not found. Valid agents are: {', '.join(valid_agents)}"
            
            # Get the agent object
            target_agent = self.agent_registry[agent_role]
            
            # Format a simpler message that will work with any agent
            formatted_message = f"Message from Product Manager: {message}"
            
            # Get the current project if available
            current_project = None
            if self.project_manager:
                current_project = self.project_manager.current_project
            
            # Call the agent's chat method if available, fallback to execute
            if hasattr(target_agent, "chat") and callable(target_agent.chat):
                response = await target_agent.chat(formatted_message)
            elif hasattr(target_agent, "execute") and callable(target_agent.execute):
                response = await target_agent.execute(formatted_message)
            else:
                return f"Error: Agent '{agent_role}' does not support communication."
            
            # Record this communication when possible
            try:
                from memory.mongo_memory import add_message
                add_message(
                    f"pm_to_{agent_role}", 
                    formatted_message, 
                    response,
                    current_project
                )
            except Exception as e:
                print(f"Error recording communication: {str(e)}")
            
            # Add to project context
            self.project_context.setdefault("communications", []).append({
                "timestamp": self._get_timestamp(),
                "from": "productManager",
                "to": agent_role,
                "message": message,
                "response": response
            })
            
            return response
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in agent-to-agent communication: {str(e)}\n{error_details}")
            return f"Error communicating with {agent_role}: {str(e)}"
    
    async def assign_and_start_task(self, agent_role: str, task: str) -> str:
        """Assign a task to a specific agent and get their immediate response"""
        try:
            # Validate that the agent exists
            if agent_role not in self.agent_registry:
                valid_agents = list(self.agent_registry.keys())
                return f"Error: Agent '{agent_role}' not found. Valid agents are: {', '.join(valid_agents)}"
            
            # Get the agent object
            target_agent = self.agent_registry[agent_role]
            
            # Format a simple task message that will work with any agent
            task_message = f"Task Assignment from Product Manager: {task}"
            
            # Get the current project if available
            current_project = None
            if self.project_manager:
                current_project = self.project_manager.current_project
            
            # Create a task object
            task_obj = {
                "name": task[:50] + "..." if len(task) > 50 else task,
                "description": task,
                "assigned_to": agent_role,
                "assigned_by": "productManager",
                "status": "in_progress",
                "created_at": self._get_timestamp()
            }
            
            # Store the task in the database if we have a current project
            if current_project and self.project_manager:
                try:
                    self.project_manager.add_task(current_project, task_obj)
                except Exception as e:
                    print(f"Error adding task to project: {str(e)}")
            
            # Call the agent's chat method if available, fallback to execute
            if hasattr(target_agent, "chat") and callable(target_agent.chat):
                response = await target_agent.chat(task_message)
            elif hasattr(target_agent, "execute") and callable(target_agent.execute):
                response = await target_agent.execute(task_message)
            else:
                return f"Error: Agent '{agent_role}' does not support task assignment."
            
            # Record this task assignment when possible
            try:
                from memory.mongo_memory import add_message
                add_message(
                    f"pm_task_to_{agent_role}", 
                    task_message, 
                    response,
                    current_project
                )
            except Exception as e:
                print(f"Error recording task assignment: {str(e)}")
            
            # Update the project context
            if "task_assignments" not in self.project_context:
                self.project_context["task_assignments"] = []
            
            self.project_context["task_assignments"].append({
                "timestamp": self._get_timestamp(),
                "task": task,
                "agent_role": agent_role,
                "response": response,
                "project": current_project
            })
            
            return response
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in task assignment: {str(e)}\n{error_details}")
            return f"Error assigning task to {agent_role}: {str(e)}"
    
    async def coordinate_multi_agent_task(self, task: str, agents: List[str]) -> Dict[str, str]:
        """MCP coordination: Orchestrate a task requiring multiple agents"""
        if not self.agent_registry or not all(agent in self.agent_registry for agent in agents):
            return {"error": "Not all specified agents are available"}
        
        # Get product manager's custom name if available
        try:
            pm_name_info = await get_team_member_name(self.role)
            pm_name = pm_name_info["name"] if pm_name_info else "Product Manager"
        except Exception:
            pm_name = "Product Manager"
            
        # Store task in project context
        if "mcp_tasks" not in self.project_context:
            self.project_context["mcp_tasks"] = []
        
        task_id = f"task_{len(self.project_context.get('mcp_tasks', []))+1}"
        
        # Create task in project manager
        if self.project_manager and self.project_manager.current_project:
            for agent_role in agents:
                # Get agent's custom name if available
                try:
                    agent_name_info = await get_team_member_name(agent_role)
                    agent_name = agent_name_info["name"] if agent_name_info else agent_role
                except Exception:
                    agent_name = agent_role
                    
                self.project_manager.add_task(
                    self.project_manager.current_project,
                    {
                        "name": f"{task_id}_{agent_name}",
                        "description": task,
                        "assigned_to": agent_role,
                        "assigned_to_name": agent_name,
                        "assigned_by": self.role,
                        "assigned_by_name": pm_name,
                        "status": "pending"
                    }
                )
        
        # Execute task with each agent
        results = {}
        agent_names = {}
        for agent_role in agents:
            agent = self.agent_registry[agent_role]
            
            # Get agent's custom name if available
            try:
                agent_name_info = await get_team_member_name(agent_role)
                agent_name = agent_name_info["name"] if agent_name_info else agent_role
                agent_names[agent_role] = agent_name
            except Exception:
                agent_name = agent_role
                agent_names[agent_role] = agent_role
                
            # Format task for the specific agent
            agent_task = f"[MCP TASK {task_id} from {pm_name}] As part of a coordinated multi-agent task: {task}"
            response = await agent.execute(agent_task)
            results[agent_role] = response
        
        # Record the task and results
        self.project_context["mcp_tasks"].append({
            "task_id": task_id,
            "description": task,
            "assigned_agents": agents,
            "agent_names": agent_names,
            "results": results,
            "status": "completed",
            "coordinator": pm_name,
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
