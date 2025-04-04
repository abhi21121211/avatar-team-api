from memory.chromadb_memory import MemoryStorage

memory = MemoryStorage()

# Store results in memory

# tasks/migration_tasks.py

from agents.chief_architect import ChiefArchitect
from agents.frontend_engineer import FrontendEngineer
from agents.backend_engineer import BackendEngineer
from agents.devops_engineer import DevOpsEngineer
from agents.ai_ml_engineer import aIMLEngineer
from agents.product_manager import ProductManager
from agents.ui_ux_designer import uIUXDesigner
from agents.technical_writer import TechnicalWriter
from agents.customer_success import CustomerSuccess
from agents.marketing_sales import MarketingSales
from agents.legal_compliance import legalCompliance

# Initialize all agents
chief_architect = ChiefArchitect()
frontend_engineer = FrontendEngineer()
backend_engineer = BackendEngineer()
devops_engineer = DevOpsEngineer()
ai_ml_engineer = aIMLEngineer()
product_manager = ProductManager()
ui_ux_designer = uIUXDesigner()
technical_writer = TechnicalWriter()
customer_success = CustomerSuccess()
marketing_sales = MarketingSales()
legal_compliance = legalCompliance()

# Define tasks for the Avatar migration project
tasks = {
    "System Architecture": chief_architect.run("Design the Avatar migration system with scalability & efficiency."),
    "Frontend Development": frontend_engineer.run("Develop Next.js UI for the Avatar migration dashboard."),
    "Backend Development": backend_engineer.run("Develop secure backend APIs for Avatar migration using Java/Node.js."),
    "DevOps Deployment": devops_engineer.run("Set up CI/CD, infrastructure, and cloud deployment for Avatar."),
    "AI Model Optimization": ai_ml_engineer.run("Optimize AI/ML models for Avatar migration automation."),
    "Product Roadmap": product_manager.run("Define the roadmap & milestones for Avatar."),
    "UI/UX Design": ui_ux_designer.run("Create user-friendly designs & wireframes for Avatar."),
    "Documentation": technical_writer.run("Write user guides & developer documentation for Avatar."),
    "Customer Support": customer_success.run("Assist clients in the migration process."),
    "marketing&Sales": marketing_sales.run("Develop a marketing strategy for Avatar migration."),
    "legalCompliance": legal_compliance.run("Ensure security, compliance, and legal adherence for Avatar."),
}



# Store results
results = {task: result for task, result in tasks.items()}

for task_name, result in tasks.items():
    memory.save_task_result(task_name, result)