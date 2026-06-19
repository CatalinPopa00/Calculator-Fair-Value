import os
import json
from dotenv import load_dotenv

# Try to load environment variables (for local development)
for base_dir in [os.getcwd(), os.path.dirname(os.path.dirname(__file__))]:
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break

try:
    from upstash_redis import Redis
except ImportError:
    Redis = None

def get_redis_client():
    url = os.environ.get("KV_REST_API_URL")
    token = os.environ.get("KV_REST_API_TOKEN")
    
    if Redis and url and token:
        try:
            return Redis(url=url, token=token)
        except Exception as e:
            print(f"Error initializing Redis client: {e}")
            return None
    return None

def get_cached_data(key: str):
    """Fetch data from cache. Returns parsed dict/string or None."""
    client = get_redis_client()
    if not client:
        return None
    
    try:
        data = client.get(key)
        if data:
            return data
    except Exception as e:
        print(f"Error reading from Redis cache ({key}): {e}")
    
    return None

def set_cached_data(key: str, data, ttl_seconds: int = 86400 * 3): # Default to 3 days (refresh rate)
    """Save data to cache with a Time-To-Live (TTL) in seconds."""
    client = get_redis_client()
    if not client:
        return False
    
    try:
        client.set(key, data, ex=ttl_seconds)
        return True
    except Exception as e:
        print(f"Error writing to Redis cache ({key}): {e}")
        return False
