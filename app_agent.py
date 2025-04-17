from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uvicorn
import json
from dotenv import load_dotenv
load_dotenv()
# Import from other project files
from my_agent.utils.nodes import *
import my_agent.agent as agent
# POSTGRES SQL
import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from asyncpg import create_pool
from asyncpg.pool import Pool
# Environment settings for Postgres
os.environ['PSQL_USERNAME'] = os.getenv('PSQL_USERNAME')
os.environ['PSQL_PASSWORD'] = os.getenv('PSQL_PASSWORD')
os.environ['PSQL_HOST'] = os.getenv('PSQL_HOST')
os.environ['PSQL_PORT'] = os.getenv('PSQL_PORT')
os.environ['PSQL_DATABASE'] = os.getenv('PSQL_DATABASE')
os.environ['PSQL_SSLMODE'] = os.getenv('PSQL_SSLMODE')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create a global connection pool."""
    try:  
        pool = AsyncConnectionPool(
          # The format of the connection string is:
          # "postgres://<username>:<password>@<host>:<port>/<database>?<options>"
          conninfo=f"postgres://{os.environ['PSQL_USERNAME']}:{os.environ['PSQL_PASSWORD']}"
          f"@{os.environ['PSQL_HOST']}:{os.environ['PSQL_PORT']}/{os.environ['PSQL_DATABASE']}"
          f"?sslmode={os.environ['PSQL_SSLMODE']}",
          max_size=20,  # Maximum number of connections in the pool
          kwargs={
              "autocommit": True,
              "prepare_threshold": 0,
              "row_factory": dict_row,
          },
          )
        memory = AsyncPostgresSaver(pool)
        #await memory.setup() # Call this only the first time you run this file.
        graph = agent.graph_builder.compile(checkpointer=memory)
        thread_config = {"configurable": {"thread_id": "1"}}
        app.state.pool = pool
        app.state.memory = memory
        app.state.graph = graph
        app.state.thread_config = thread_config
        app.state.pending_response = {}
        yield
    except Exception as e:
        print(f'Exception occured: {e}')
    finally:
        if pool:
            try:
                await asyncio.wait_for(pool.close(), timeout = 10.)
            except asyncio.TimeoutError:
                print('Timeout error')

connected_clients = {}    
app = FastAPI(lifespan=lifespan) 
app.mount("/static", StaticFiles(directory= "static"), name= "static")
templates = Jinja2Templates(directory="templates")

# Customer page
@app.get("/")
async def chat(request: Request):
    return templates.TemplateResponse(request=request, name="user.html", context={})
# Backoffice page
@app.get("/backoffice")
async def backoffice_chat(request: Request):
    return templates.TemplateResponse(request=request, name="backoffice.html", context={"pendingQuestions": app.state.pending_response})
# Websocket
@app.websocket("/ws/{client_id}")
async def ask(websocket: WebSocket, client_id):
    await websocket.accept()
    connected_clients[client_id] = websocket
    graph = websocket.scope['app'].state.graph
    thread_config = websocket.scope['app'].state.thread_config
    pool = websocket.scope['app'].state.pool
    while True:
        try:   
            data = await websocket.receive_text()
            data = json.loads(data)
            if '-backoffice' in client_id: # Back-office management
                async with pool.connection() as conn:
                    #data = json.loads(data)
                    response = await agent.human_response(graph = graph, thread_config= thread_config, backoffice_response= data['response'])
                    clientid_to_answer = data['clientId']
                    client_websocket = connected_clients[clientid_to_answer] 
                    await client_websocket.send_text(response)
                    del websocket.scope['app'].state.pending_response[clientid_to_answer]
            else: # Customer block
                async with pool.connection() as conn:
                    result = await agent.run_chatbot(graph = graph, thread_config= thread_config, question = data['response'])
                    response = result['response']
                    await websocket.send_text(response)                    
                    if result['is_interrupted']: # This block is needed for handling human in the loop
                        websocket.scope['app'].state.pending_response[client_id] = data['response']
        except WebSocketDisconnect:
            del connected_clients[client_id]
            print(f'Client {client_id} disconnected')
            if len(connected_clients) == 0:
                await websocket.close()
        except Exception as e:
            response = f"Error: {e.args}"
            await websocket.send_text(response)   

if __name__ == "__main__":
    uvicorn.run('app_agent:app', port = 8000, reload = True)