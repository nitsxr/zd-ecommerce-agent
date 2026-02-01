E-commerce Assistant Challenge: Building a Production-Ready
Multi-Agent System

Welcome to the challenge! Your task is to design and build a robust, observable, and
production-ready system to handle customer service inquiries for an e-commerce platform.
This system must be capable of managing complex, multi-turn conversations and fulfilling
user requests based on defined business policies.

The Core System
The core of your system must handle the following business logic and policies. The design
should hint at a multi-component architecture, where a primary orchestrator delegates tasks
to specialized components.
● Order Cancellation Policy:
○ The system must ask the user for an order ID and validate that it's in the format
ORD-XXXX (e.g., ORD-1234).
○ An order can only be canceled if it was placed less than 24 hours ago.
○ It should interact with a mock API to process the cancellation and inform the user of
the result.
● Order Tracking Policy:
○ The system must ask the user for an order ID and validate that it's in the format
ORD-XXXX (e.g., ORD-1234).
○ It should interact with a mock API to retrieve and provide the order's status and
estimated delivery date.
● Product Information Policy:
○ The system must be able to answer frequently asked questions or product-specific
queries by retrieving information from a knowledge base.
○ You can implement this with a simple JSON document containing Q&A pairs and
string search, or a more advanced Retrieval-Augmented Generation (RAG) system
using embeddings.

Business Logic Example: You are free to build API using to mock servers like
https://beeceptor.com/

Architecture and State Management

Your system's architecture should be designed with a clear separation of concerns, hinting at
a multi-agent approach.
To support multi-turn conversations, your system must maintain conversational state and
context. This is crucial for scenarios like:
● Turn 1: A user asks a question about a product (e.g., "Can I return my Bluetooth
headphones?").
● Turn 2: The user follows up with, "Alright, cancel the order for that then."
The system should be able to recall the product context ("Bluetooth headphones") from the
first turn and use it to execute the request in the second turn.
● Your agents must generate structured, predictable outputs
● Add documentation how multi turn and state management is handled between agents
OBSERVABILITY : Your application must be observable. Implement logging for key events

Testing Interface & Evaluation Criteria

Your system should expose a single HTTP endpoint that accepts user messages and returns
system responses.
🧵 Endpoint Specification
● Endpoint: POST /chat
● Example Request Payload:

{
"session_id": "abc123",
"message": "I want to cancel my order ORD-4567"
}

● Example Response Payload:
{
"response": "Sure, I can help with that. Let me check if your
order is eligible for cancellation.",
"agent": "OrderCancellationAgent",
"tool_calls": [
{
"tool": "OrderCancellationAPI",
"input": { "orderId": "ORD-4567" },
"result": { "status": "cancelled", "refunded": true }
}
],
"handover": "OrchestratorAgent → OrderCancellationAgent"
}

session_id is used to maintain conversational context and memory across turns.
You may use an in-memory store or Redis to persist state keyed by session.

Evaluation Criteria

Scenario fitness: How does your solution meet the requirements?
Modularity: Can your code easily be modified? How much effort is needed to add a new kind
of ML model to your inference service?
Code readability and comments: Is your code easily comprehensible and structured for
maintainability?
Robustness: Does your solution demonstrate reliability and consideration for edge cases?
Bonus: Any additional creative features: Docker files, architectural diagrams, Swagger, agent
performance metrics etc.

What to Submit
Provide a link to a private GitHub repository containing:
● All source code for the mukti-agent system and mock APIs. Do not use any third-party
agent libraries; build the agents from scratch. You are free to use other OpenAI SDKs or
similar tools.
● A detailed README.md that includes:

○ An architecture diagram and an explanation of your design choices.
○ Clear instructions on how to build and run the system
○ The defined structured output (JSON) schemas for your agents
○ A Dockerfile and docker-compose.yml to package and run your solution