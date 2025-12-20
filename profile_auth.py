
import asyncio
import timeit
from unittest.mock import Mock
from app.routers.auth import get_current_user
from itsdangerous import TimestampSigner
from app.config import settings
import json

# Replace the original signer with a mock for profiling
signer = TimestampSigner(settings.security.secret_key)

# Create a mock request with a valid session cookie
session_data = {"user_id": 1, "username": "testuser", "is_admin": False}
session_cookie = signer.sign(json.dumps(session_data).encode("utf-8"))
mock_request = Mock()
mock_request.cookies = {"session": session_cookie.decode("utf-8")}

# Define the async function to be profiled
async def func_to_profile():
    await get_current_user(mock_request)

# Synchronous wrapper for timeit
def sync_wrapper():
    asyncio.run(func_to_profile())

# Run the profiler
iterations = 1000
total_time = timeit.timeit(sync_wrapper, number=iterations)
avg_time = total_time / iterations

print(f"--- Asynchronous get_current_user ---")
print(f"Total time for {iterations} iterations: {total_time:.4f} seconds")
print(f"Average time per call: {avg_time * 1e6:.2f} microseconds")
