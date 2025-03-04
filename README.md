# Forward Deployed Engineer Take Home

## Overview

While Brainbase supports an extensive suite of 100+ built-in integrations, our legacy enterprise customers sometimes require tailored integrations with outdated software—often lacking robust documentation.

As a Forward Deployed Engineer, you’ll be at the forefront of prototyping, testing, and launching these custom integrations to our LLMs. You’ll turn incomplete API documentation, cryptic error logs, and ambiguous payload parameters into seamless, high-performance solutions - immune to the stochastic nature of LLMs and AI. Our customers demand unwavering accuracy, bulletproof reliability, and an absolute zero tolerance for 500 Internal Server Errors or failed requests.

## The Challenge

Brainbase has just signed a new customer, Based Airlines, who uses a legacy API to manage their flight bookings, fetch flight data, and upsell services provided by their partners (such as hotel rooms and rental cars).  

They have requested a chat bot where customers can come to book full flight itineraries, as well as add on services such as hotel rooms and rental cars.

Based Airline has requested that we use the [Amadeus](https://developers.amadeus.com/) API to take these actions.

All the customer was able to provide for context was this link:
https://developers.amadeus.com

Oh, and this video!...requesting that we skip to 1:23 for some inspiration:
[![Falco - Rock Me Amadeus](https://img.youtube.com/vi/cVikZ8Oe_XA/0.jpg)](https://www.youtube.com/watch?v=cVikZ8Oe_XA)


## Installing the template

### Prerequisites

Make sure to **clone** and not fork this repo. You can do this by clicking the `Code` button and selecting `Download ZIP`, or copy the path, and run:

```bash
git clone https://github.com/...
```

Ensure you have python, node, and npm installed.

### Backend

```bash
pip install -r requirements.txt
```

### Frontend

```bash
npm install
```

### Running the application
To run the client, navigate to /frontend and run:

```bash
npm start
```

To run the server, navigate to /backend and run:

```bash
uvicorn app.main:app --reload
```

## Problem Statement

How can Brainbase interface with live travel data and behave as a real life travel agent would?


## Intructions

You are to build anAI chat that connects to real time travel data provided by the Amadeus API
https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/

You will need to get an API key with a self-service app (should be completely free)

1. Implement the Amadeus API integration in the backend/app/custom_tools.py file.
2. Implement the Amadeus API integration in the backend/app/main.py file so that the agent can call the tools.

You can edit the SYSTEM_PROMPT in the backend/app/main.py file to change the behavior of the agent, and provide tools via the AVAILABLE_FUNCTIONS variable.


## Milestones

### Milestone 1: Implement the Amadeus API integration
Implement at least 2 of the following Amadeus API resources:
- Flights
- Transports
- Hotels
- Experiences

Be creative with the tools you implement, defining functions that take in multiple parameters and can be used to complete more complex queries. You can implement this in the backend/app/custom_tools.py file.


https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/resources

Ideally, we want to see a tool that can complete the entire flow of booking a flight, hotel, and rental car. Build this tool as if it were a real product that a customer would use.

### Milestone 2: Allow the LLM to use the integration at will

The agent should be able to use the Amadeus API integration to complete the task when queried by the user. We should be able to chat with the AI agent to book a flight, hotel, and rental car.


### Milestone 3: Allow the agents to call complex, multi layer functions

The agent should be able to take actions that require multiple API calls to complete, and be successful at least 90% of the time. This means that we can query the agent with less than perfect queries, not including all of the information needed to complete the action, or going off topic. It should be extremeley robust to human or LLM error, and able to complete the task.


## Deliverable

Either a new github repo or a zip file containing the entire codebase with instructions on how to run it locally, emailed to matt@usebrainbase.xyz. After submission, the brainbase team should be able to run the code locally and chat with the agent, without any additional setup. **Please do not make a PR into this codebase or fork the codebase ** 


## Notes:

This is a starter template for you to build on. You can edit any files within this codebase, or start from scratch using any stack you would like. However, we recommend using this template to build on top of. 

We have also emailed you an OpenAI API key for you to use, but if you want to use a different LLM, feel free to do so. 

If you have any questions, feel free to reach out to us via email at matt@usebrainbase.xyz

Good luck!
