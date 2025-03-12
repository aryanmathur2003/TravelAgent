from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from .models import ChatRequest, ChatMessage
from .openai_service import generate_chat_response
from .custom_tools import search_flights, book_flight
from .hotel_requests import search_hotels, book_hotel, search_hotel_offers
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
from datetime import datetime

# ✅ Get today's date dynamically
# today_date = datetime.today().strftime("%Y-%m-%d")
# logger.info(f"******************DATE TODAY : {today_date}")
SYSTEM_PROMPT = """You are a helpful AI assistant that helps users search and book flights and hotels.

- When the user requests flights or hotels, you will store the full list of results internally.
- If the user wants to book a flight, use the stored flight ID from the cache instead of calling 'search_flights' again.
- If the user wants to book a hotel, first use 'search_hotels' to find available hotels.
- To get available rooms or offers, use 'search_hotel_offers' with the correct hotel ID.
- If the cache is empty or expired, THEN you can call 'search_hotels' again.
"""




# Define available functions/tools
AVAILABLE_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_flights",
            "description": "Search for available flights based on the origin, destination, departure date, and maximum price. "
                        "If the user does not provide a date, ask them to clarify. "
                        "Do not assume or guess the date — only use the date explicitly provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "The IATA code of the departure airport (e.g., 'JFK')."
                    },
                    "destination": {
                        "type": "string",
                        "description": "The IATA code of the destination airport (e.g., 'MAD'). "
                                    "If missing, suggest popular destinations or ask the user for clarification."
                    },
                    "departure_date": {
                        "type": "string",
                        "description": "Date of flight (YYYY-MM-DD). Must be explicitly provided by the user."
                    },
                    "max_price": {
                        "type": "integer",
                        "description": "The maximum price for flights in the preferred currency."
                    }
                },
                "required": ["origin", "destination", "departure_date", "max_price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_flight",
            "description": "Book a flight using the ID and passenger details. "
                           "If the ID is missing, call 'search_flights' to find the available flights first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "The unique flight ID for booking (e.g., '1')."
                    },
                    "passenger_name": {
                        "type": "string",
                        "description": "Full name of the passenger for booking."
                    }
                },
                "required": ["booking_id", "passenger_name"]
            }
        }
    },
        {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": "Search for available hotels based on city, geocode, or hotel ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_code": {
                        "type": "string",
                        "description": "The IATA code of the destination city (e.g., 'NYC')."
                    },
                    "latitude": {
                        "type": "number",
                        "description": "Latitude for geocode-based search."
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude for geocode-based search."
                    },
                    "hotel_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of hotel IDs for direct lookup."
                    }
                },
                "required": []
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_next_hotel_results",
            "description": "Get the next batch of hotel search results."
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_hotel_offers",
            "description": "Get available room offers for specific hotels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hotel_ids": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of hotel_id to search for offers. Do not use the hotel name but map the name to the hotel_id given previously"
                    },
                    "check_in_date": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format. Must be in the future. Must be explicitly provided by the user."
                    },
                    "check_out_date": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format. Must be after the check-in date. Must be explicitly provided by the user."
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult guests."
                    }
                },
                "required": ["hotel_ids", "check_in_date", "check_out_date", "adults"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_hotel",
            "description": "Book a hotel using an offer ID and guest details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "offer_id": {
                        "type": "string",
                        "description": "offer_ID is a 10 digit code for the selected offer. The offer_id is given: If offer_id is NA search for more offers"
                    },
                    "guests": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tid": {
                                    "type": "integer",
                                    "description": "Guest reference ID."
                                },
                                "title": {
                                    "type": "string",
                                    "description": "Title (e.g., 'MR', 'MRS')."
                                },
                                "firstName": {
                                    "type": "string",
                                    "description": "Guest's first name."
                                },
                                "lastName": {
                                    "type": "string",
                                    "description": "Guest's last name."
                                },
                                "phone": {
                                    "type": "string",
                                    "description": "Guest's phone number."
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Guest's email address."
                                }
                            },
                            "required": ["tid", "title", "firstName", "lastName", "phone", "email"]
                        },
                        "description": "List of guests for the booking."
                    }
                },
                "required": ["offer_id", "guests"]
            }
        }
    }
]





# Map function names to their implementations
FUNCTION_MAP = {
    "search_flights": search_flights,
    "book_flight": book_flight
    
}
FUNCTION_MAP["search_hotels"] = search_hotels
FUNCTION_MAP["book_hotel"] = book_hotel
FUNCTION_MAP["search_hotel_offers"] = search_hotel_offers



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
            
            logger.info(f"Received WebSocket message: {data}")  # Log the first 100 chars
            
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
                
                # Add system prompt if not already present
                if not any(msg.role == "system" for msg in follow_up_messages):
                    follow_up_messages.insert(0, ChatMessage(role="system", content=SYSTEM_PROMPT))
                #     logger.info("********* SYSTEM IS INSTERTED AND FOLLOW UP IS RUN")
                # logger.info(f"********* FOLLOW UP IS RUN {follow_up_messages}")
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
            content = response.get("content") or "I'm sorry, I couldn't understand that. Please try again."
            
            # Log what we're sending to help debug
            logger.info(f"Sending message to client: {content}")
            
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