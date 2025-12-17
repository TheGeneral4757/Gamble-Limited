import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.core.database import db

def create_test_user():
    """Creates a test user with default credentials."""
    username = "testuser"
    password = "password"

    if db.username_exists(username):
        print(f"User '{username}' already exists.")
        return

    result = db.create_user(username, password)

    if result.get("success"):
        print(f"Successfully created user '{username}' with password '{password}'.")
    else:
        print(f"Failed to create user: {result.get('error')}")

if __name__ == "__main__":
    create_test_user()
