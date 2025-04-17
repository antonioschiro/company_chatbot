#                                                   CUSTOMER ASSISTANT CHATBOT
This project showcases a customizable assistant chatbot built for a fictional company called Quantum Technologies, which specializes in selling hard drives.
The chatbot is designed to:

1. Provide detailed information about company products (pricing, discounts, employees);

2. Share insights on the company’s history and employees;

3. Answer general questions related to hard drives, tech and IT;

This project is highly adaptable and can be easily tailored to suit any company or domain.

## Chatbot Architecture
The assistant is built using LangChain and LangGraph — two powerful Python frameworks for building modular LLM applications with flow control.
It leverages LLaMA as the LLM and consists of three main flows:

1. Retrieval-Augmented Generation (RAG)
This flow handles questions related to company-specific information by querying a vector database.
I implemented a multi-query RAG strategy: the chatbot generates three different rephrasings of the user’s original question.
Each query performs separate retrievals from the vector store.
The results are merged to build a more complete answer context.

2. General Chatbot Flow
This branch handles queries not directly related to the company, such as:
    a. Technical details about hard drives;
    b. Broader IT and programming topics.

The model also has access to a web search tool to enrich its responses with up-to-date external information.

3. Human-in-the-Loop (HITL)
When the model cannot confidently answer a question, it triggers a flow interruption and delegates the task to a human assistant.
This typically happens when:

    a. Users ask for a custom offer;

    b. The chatbot is explicitly asked to escalate to a human-

## Memory & Persistence
The assistant uses a PostgreSQL database to store persistent memory, allowing it to remember context between sessions.

## Project Stack & Real-Time Interaction
To support real-time interaction between users and the assistant, I built a websocket API using FastAPI.
Users can interact with the assistant in two roles:

1. Customer;

2. Back-office human assistant.

## Final considerations
This project blends retrieval-augmented generation, human-in-the-loop, and memory capabilities into a robust assistant — and is easily extensible for real-world business use.