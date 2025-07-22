import asyncio
import sys
from utils.database import connect_to_mongodb, close_mongodb_connection, create_team_member_name, get_all_team_member_names

async def set_team_member_name(role, name):
    """Set a team member's custom name"""
    await connect_to_mongodb()
    result = await create_team_member_name(role, name)
    print(f"Set name for {role} to '{name}'")
    return result

async def list_team_member_names():
    """List all team member names"""
    await connect_to_mongodb()
    names = await get_all_team_member_names()
    
    if not names:
        print("No team member names found.")
        return
    
    print("\nTeam Member Names:")
    print("=" * 50)
    print(f"{'Role':<20} | {'Name':<30}")
    print("-" * 50)
    
    for name_info in names:
        print(f"{name_info['role']:<20} | {name_info['name']:<30}")
    
    print("=" * 50)

async def update_multiple_names(name_dict):
    """Update multiple team member names at once"""
    await connect_to_mongodb()
    for role, name in name_dict.items():
        await create_team_member_name(role, name)
    
    print(f"Updated {len(name_dict)} team member names.")

async def main():
    """Main function to run the script"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python update_team_names.py list")
        print("  python update_team_names.py set <role> <name>")
        print("  python update_team_names.py update_all")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        await list_team_member_names()
    
    elif command == "set" and len(sys.argv) >= 4:
        role = sys.argv[2]
        name = " ".join(sys.argv[3:])
        await set_team_member_name(role, name)
    
    elif command == "update_all":
        # Example preset names - modify as needed
        custom_names = {
            "chiefArchitect": "System Architect",
            "frontendEngineer": "UI Developer",
            "backendEngineer": "API Engineer",
            "devopsEngineer": "Infrastructure Specialist",
            "aiMlEngineer": "AI Specialist",
            "productManager": "Project Lead",
            "uiUxDesigner": "Design Expert",
            "technicalWriter": "Documentation Specialist",
            "customerSuccess": "User Support",
            "legalCompliance": "Legal Advisor",
            "marketingSales": "Marketing Specialist"
        }
        
        await update_multiple_names(custom_names)
        await list_team_member_names()
    
    else:
        print("Invalid command. Use 'list', 'set <role> <name>', or 'update_all'.")

if __name__ == "__main__":
    asyncio.run(main()) 