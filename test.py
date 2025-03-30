import os
from dotenv import load_dotenv

load_dotenv("credentials.env")  # Ensure correct filename
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    print("API Key Loaded Successfully:", api_key)
else:
    print("API Key NOT LOADED. Check credentials.env")
