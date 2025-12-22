import sys
import os
import asyncio

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.core.database import db

async def create_test_user():
    """Creates a test user with default credentials."""
    username = "testuser"
    password = "password"

    # db.create_user already checks for existing users
    result = await db.create_user(username, password)

    if result.get("success"):
        print(f"Successfully created user '{username}' with password '{password}'.")
    elif result.get("error") == "Username already taken":
        print(f"User '{username}' already exists.")
    else:
        print(f"Failed to create user: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(create_test_user())
