from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from .models import ChatRequest, ChatMessage
from .openai_service import generate_chat_response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define global system prompt
SYSTEM_PROMPT = """You are a helpful AI assistant. You can answer questions, provide information, 
and help with various tasks. If you don't know the answer to something, just say so instead of making up information.
You can use tools when appropriate to fulfill user requests."""

# Define available functions/tools
AVAILABLE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location if the user asks for it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information on a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# Function implementations
async def get_weather(location, unit="celsius"):
    # This would be replaced with actual API call to weather service
    logger.info(f"Getting weather for {location} in {unit} units")
    return {
        "location": location,
        "temperature": "22" if unit == "celsius" else "72",
        "unit": unit,
        "condition": "sunny"
    }

async def search_web(query):
    # This would be replaced with actual web search API
    logger.info(f"Searching web for: {query}")
    return {
        "query": query,
        "results": [
            {"title": "Example result 1", "snippet": "This is an example search result."},
            {"title": "Example result 2", "snippet": "Another example search result."}
        ]
    }

# Map function names to their implementations
FUNCTION_MAP = {
    "get_weather": get_weather,
    "search_web": search_web
}


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)


manager = ConnectionManager()


@app.get("/")
async def root():
    return {"message": "Welcome to the Chat API"}


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            data_json = json.loads(data)
            
            logger.info(f"Received WebSocket message: {data[:100]}...")  # Log the first 100 chars
            
            # Convert the received data to our models
            messages = []
            for msg in data_json.get("messages", []):
                # Handle different message structures
                try:
                    # Create a dictionary with only the fields that exist in the message
                    message_data = {"role": msg["role"]}
                    
                    # Add content if it exists
                    if "content" in msg:
                        # Check if content is a nested dictionary with its own content field
                        if isinstance(msg["content"], dict) and "content" in msg["content"]:
                            message_data["content"] = msg["content"]["content"]
                        else:
                            message_data["content"] = msg["content"]
                    else:
                        message_data["content"] = None
                    
                    # Add tool_calls if they exist
                    if "tool_calls" in msg:
                        message_data["tool_calls"] = msg["tool_calls"]
                    
                    # Add tool_call_id if it exists
                    if "tool_call_id" in msg:
                        message_data["tool_call_id"] = msg["tool_call_id"]
                    
                    # Create the ChatMessage with the appropriate fields
                    chat_message = ChatMessage(**message_data)
                    messages.append(chat_message)
                except Exception as e:
                    logger.error(f"Error creating ChatMessage: {str(e)}, message data: {msg}")
                    raise
            
            # Add system prompt if not already present
            if not any(msg.role == "system" for msg in messages):
                messages.insert(0, ChatMessage(role="system", content=SYSTEM_PROMPT))
            
            # Create the chat request with tools
            chat_request = ChatRequest(
                messages=messages,
                model=data_json.get("model", "gpt-3.5-turbo"),
                temperature=data_json.get("temperature", 0.7),
                tools=AVAILABLE_FUNCTIONS  # Add tools to the request
            )
            
            # Log the request being sent to OpenAI
            logger.info(f"Sending request to OpenAI with tools: {len(AVAILABLE_FUNCTIONS)} tools included")
            
            # Send acknowledgment that message was received
            await websocket.send_json({
                "type": "message_received",
                "message": "Processing your request..."
            })
            
            # Generate response from OpenAI
            response = await generate_chat_response(chat_request)
            
            # Log the raw response for debugging
            logger.info(f"Raw response from OpenAI: {response}")
            
            # Check if the response contains a function call
            if response.get("tool_calls"):
                logger.info(f"Response contains tool calls: {response['tool_calls']}")
                
                # Create a new list of messages for the follow-up request
                follow_up_messages = messages.copy()  # Start with the original messages
                
                # Add the assistant response with tool_calls
                assistant_message_dict = {
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": response.get("tool_calls")
                }
                follow_up_messages.append(ChatMessage(**assistant_message_dict))
                
                # Process each tool call
                for tool_call in response.get("tool_calls", []):
                    try:
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])
                        
                        logger.info(f"Executing function: {function_name} with args: {function_args}")
                        
                        # Execute the function if it exists in our map
                        if function_name in FUNCTION_MAP:
                            function_response = await FUNCTION_MAP[function_name](**function_args)
                            
                            # Add the tool response
                            tool_message_dict = {
                                "role": "tool",
                                "content": json.dumps(function_response),
                                "tool_call_id": tool_call["id"]
                            }
                            follow_up_messages.append(ChatMessage(**tool_message_dict))
                    except Exception as e:
                        logger.error(f"Error executing function {function_name}: {str(e)}")
                        # Add an error message as the tool response
                        tool_message_dict = {
                            "role": "tool",
                            "content": json.dumps({"error": str(e)}),
                            "tool_call_id": tool_call["id"]
                        }
                        follow_up_messages.append(ChatMessage(**tool_message_dict))
                
                # Create a new request with the updated messages
                follow_up_request = ChatRequest(
                    messages=follow_up_messages,
                    model=chat_request.model,
                    temperature=chat_request.temperature,
                    tools=chat_request.tools
                )
                
                # Get a new response with the function results
                try:
                    logger.info("Sending follow-up request with tool results")
                    response = await generate_chat_response(follow_up_request)
                except Exception as e:
                    logger.error(f"Error getting final response after tool calls: {str(e)}")
                    response = {"content": f"I'm sorry, I encountered an error processing your request. {str(e)}"}
            
            logger.info("Sending response back to client")
            
            # Send the response back to the client with a consistent format
            # Make sure we're sending just the content string, not a nested object
            content = response.get("content", "")
            
            # Log what we're sending to help debug
            logger.info(f"Sending message to client: {content[:100]}...")
            
            await websocket.send_json({
                "type": "chat_response",
                "message": content,  # Send just the content string
                "role": "assistant"
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {str(e)}", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 