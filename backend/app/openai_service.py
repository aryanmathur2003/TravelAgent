import os
import openai
import logging
from .models import ChatRequest

# Configure logging
logger = logging.getLogger(__name__)

# Set up OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai.api_key)

async def generate_chat_response(chat_request: ChatRequest):
    """Generate a chat response using OpenAI API."""
    try:
        # Convert Pydantic models to dictionaries for the OpenAI API
        messages = []
        for msg in chat_request.messages:
            # Create a message dictionary
            message_dict = {"role": msg.role}
            
            # Add content if it's not None
            if msg.content is not None:
                message_dict["content"] = msg.content
            
            # Add tool_calls if they exist
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            
            # Add tool_call_id if it exists
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            
            messages.append(message_dict)
        
        # Log the messages being sent to OpenAI for debugging
        logger.info(f"Sending the following messages to OpenAI:")
        for i, msg in enumerate(messages):
            logger.info(f"Message {i}: role={msg['role']}, content={msg.get('content', 'None')[:50]}...")
            if 'tool_calls' in msg:
                logger.info(f"  - Has tool_calls: {msg['tool_calls']}")
            if 'tool_call_id' in msg:
                logger.info(f"  - Has tool_call_id: {msg['tool_call_id']}")
        
        # Create parameters for the API call
        params = {
            "model": chat_request.model,
            "messages": messages,
            "temperature": chat_request.temperature,
        }
        
        # Add tools if they exist
        if chat_request.tools:
            params["tools"] = chat_request.tools
            logger.info(f"Including {len(chat_request.tools)} tools in the request")
        
        # Add tool_choice if it exists
        if chat_request.tool_choice:
            params["tool_choice"] = chat_request.tool_choice
        
        # Make the API call
        response = client.chat.completions.create(**params)
        
        # Convert the response to a dictionary
        response_dict = {
            "role": response.choices[0].message.role,
            "content": response.choices[0].message.content,
        }
        
        # Add tool_calls if they exist
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            tool_calls = []
            for tool_call in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                })
            response_dict["tool_calls"] = tool_calls
        
        return response_dict
    
    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        raise 