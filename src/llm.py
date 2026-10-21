import time
from openai import OpenAI
from . import config

_client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

def chat(messages, tools=None, temperature=0.2, retries=5):
    kwargs = dict(model=config.LLM_MODEL, messages=messages, temperature=temperature)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
        
    for attempt in range(retries):
        try:
            return _client.chat.completions.create(**kwargs)
        except Exception as e:
            if attempt == retries - 1:
                raise e # If we run out of retries, crash
            
            print(f"\n⚠️ API Error: {e}")
            print(f"Waiting 15 seconds before retrying (Attempt {attempt+1}/{retries})...")
            time.sleep(15)
