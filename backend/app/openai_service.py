import os
import openai
import logging
from dotenv import load_dotenv
from openai import OpenAIError
from .models import ChatRequest

logger = logging.getLogger(__name__)

# 1. Load environment variables
load_dotenv(".env")

# 2. Retrieve OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("Missing OPENAI_API_KEY in environment.")
    raise ValueError("Missing OPENAI_API_KEY!")

# 3. Set your API key
openai.api_key = api_key

# (Optional) proxy config if needed
PROXIES = {
    "http":  "http://proxyuser:proxypass@proxy.server:port",
    "https": "http://proxyuser:proxypass@proxy.server:port"
}

async def generate_chat_response(chat_request: ChatRequest):
    """
    Generate a chat response using openai>=1.0.0 with openai.Chat.create().
    """
    try:
        # Convert ChatRequest messages into the format expected by OpenAI
        messages = []
        for msg in chat_request.messages:
            message_dict = {"role": msg.role}
            if msg.content is not None:
                message_dict["content"] = msg.content
            # If your code or model uses these fields, keep them; otherwise they’re typically ignored
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id

            messages.append(message_dict)

        logger.info("Sending messages to OpenAI API.")

        # Build parameters
        params = {
            "model":       chat_request.model,
            "messages":    messages,
            "temperature": chat_request.temperature,
            # "request_kwargs": {"proxies": PROXIES}, # If you really need a proxy
        }

        # Note: "tools" and "tool_choice" are not standard for Chat endpoints,
        # but if your model or special server logic uses them, you can still pass them:
        if chat_request.tools:
            params["tools"] = chat_request.tools
        if chat_request.tool_choice:
            params["tool_choice"] = chat_request.tool_choice

        # The key fix: call openai.Chat.create(...)
        response = openai.chat.completions.create(**params)
        

        # The standard usage is the same: get role/content from the first choice
        role = response.choices[0].message.role
        content = response.choices[0].message.content

        # Build a dictionary with any extra info you want
        response_dict = {
            "role": role,
            "content": content
        }

        # If your specialized model or deployment returns "tool_calls", handle it here
        # e.g.:
        # if hasattr(response.choices[0].message, "tool_calls"):
        #     response_dict["tool_calls"] = response.choices[0].message.tool_calls

        return response_dict

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return {"error": "An error occurred with OpenAI API. Please try again later."}
    except Exception as e:
        logger.error(f"Unexpected error in generate_chat_response: {str(e)}")
        return {"error": "An unexpected error occurred. Please try again later."}
