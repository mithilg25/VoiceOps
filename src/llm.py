from openai import OpenAI
from . import config

_client = OpenAI(api_key=config.OPENAI_API_KEY, base_url = config.OPENAI_BASE_URL)

def chat(messages, tools = None, temperature = 0.2):
    kwargs = dict(model = config.LLM_MODEL, messages = messages, temperature = temperature)
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    return _client.chat.completions.create(**kwargs)    
