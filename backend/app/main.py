from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from .models import ChatRequest, ChatMessage
from .openai_service import generate_chat_response
from .custom_tools import search_flights, get_flight_availability, get_flight_pricing, book_flight

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
SYSTEM_PROMPT = """You are a helpful AI assistant that provides structured responses.
Always format flight search results using the following structure:

- **From:** [Origin Airport] → **To:** [Destination Airport]  
- **Departure Date:** [Departure Date]  
- **Price:** $[Price]  
---
Ensure clarity and readability in all responses.
"""

# Define available functions/tools
AVAILABLE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights based on user input.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Origin airport IATA code (e.g., 'JFK')"},
                    "destination": {"type": "string", "description": "Destination airport IATA code (e.g., 'LAX')"},
                    "departure_date": {"type": "string", "description": "Departure date in YYYY-MM-DD format"},
                    "max_price": {"type": "integer", "description": "Maximum price for flights"}
                },
                "required": ["origin", "destination", "departure_date", "max_price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_availability",
            "description": "Check flight availability using the flight number and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_number": {"type": "string", "description": "Flight number (e.g., 'AA100')"},
                    "date": {"type": "string", "description": "Date of flight (YYYY-MM-DD)"}
                },
                "required": ["flight_number", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_flight_pricing",
            "description": "Retrieve the pricing details of a specific flight.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string", "description": "ID of the flight to get pricing"}
                },
                "required": ["flight_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "description": "Book a flight based on the flight ID and passenger details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string", "description": "Flight ID to book"},
                    "passenger_name": {"type": "string", "description": "Full name of the passenger"}
                },
                "required": ["flight_id", "passenger_name"]
            }
        }
    }
]

# Map function names to their implementations
FUNCTION_MAP = {
    "search_flights": search_flights,
    "get_flight_availability": get_flight_availability,
    "get_flight_pricing": get_flight_pricing,
    "book_flight": book_flight
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
            logger.info(f"Received WebSocket message: {data}")

            messages = []
            for msg in data_json.get("messages", []):
                try:
                    message_data = {"role": msg["role"]}

                    if "content" in msg:
                        message_data["content"] = msg["content"]

                    if "tool_calls" in msg:
                        message_data["tool_calls"] = msg["tool_calls"]

                    if "tool_call_id" in msg:
                        message_data["tool_call_id"] = msg["tool_call_id"]

                    chat_message = ChatMessage(**message_data)
                    messages.append(chat_message)
                except Exception as e:
                    logger.error(f"Error creating ChatMessage: {e}, message data: {msg}")
                    raise

            # Add system prompt if not already present
            if not any(msg.role == "system" for msg in messages):
                messages.insert(0, ChatMessage(role="system", content=SYSTEM_PROMPT))

            # Create the chat request with tools
            chat_request = ChatRequest(
                messages=messages,
                model=data_json.get("model", "gpt-3.5-turbo"),
                temperature=data_json.get("temperature", 0.7),
                tools=AVAILABLE_FUNCTIONS
            )

            logger.info("Sending request to OpenAI")

            await websocket.send_json({
                "type": "message_received",
                "message": "Processing your request..."
            })

            response = await generate_chat_response(chat_request)

            if response.get("tool_calls"):
                for tool_call in response.get("tool_calls", []):
                    try:
                        function_name = tool_call["function"]["name"]
                        function_args = json.loads(tool_call["function"]["arguments"])

                        if function_name in FUNCTION_MAP:
                            function_response = await FUNCTION_MAP[function_name](**function_args)

                            tool_message_dict = {
                                "role": "tool",
                                "content": json.dumps(function_response),
                                "tool_call_id": tool_call["id"]
                            }
                            messages.append(ChatMessage(**tool_message_dict))

                    except Exception as e:
                        logger.error(f"Error executing function {function_name}: {str(e)}")
                        tool_message_dict = {
                            "role": "tool",
                            "content": json.dumps({"error": str(e)}),
                            "tool_call_id": tool_call["id"]
                        }
                        messages.append(ChatMessage(**tool_message_dict))

                follow_up_request = ChatRequest(
                    messages=messages,
                    model=chat_request.model,
                    temperature=chat_request.temperature,
                    tools=chat_request.tools
                )

                try:
                    response = await generate_chat_response(follow_up_request)
                except Exception as e:
                    logger.error(f"Error getting final response: {e}")
                    response = {"content": f"Error processing request: {e}"}

            await websocket.send_json({
                "type": "chat_response",
                "message": response.get("content", ""),
                "role": "assistant"
            })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
