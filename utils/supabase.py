from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Helper function for creating Supabase client
def get_supabase_client() -> Client:
    url: str = get_secret("SUPABASE_URL")
    key: str = get_secret("SUPABASE_KEY")
    return create_client(url, key)

# Helper function to get secret keys
def get_secret(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Secret '{key}' not found.")
    return value

# Fetch data from Supabase
def fetch_cached_data_from_supabase(table):
    supabase: Client = get_supabase_client()
    response = supabase.table(table).select("*").execute()
    return response.data

# Insert or update data
def upsert_data_to_supabase(table, data):
    supabase: Client = get_supabase_client()
    response = supabase.table(table).upsert(data).execute()
    return response.data
