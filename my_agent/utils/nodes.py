import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langgraph.graph import END
from typing_extensions import List, TypedDict, Annotated, Literal, Sequence
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from pydantic import BaseModel
from langchain.prompts import ChatPromptTemplate
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from .agent_tools import tavily_tool, vector_store
from .templates import *
# Environment settings
load_dotenv()
os.environ['LANGCHAIN_TRACING_V2'] = os.getenv('LANGCHAIN_TRACING_V2')
os.environ['LANGCHAIN_API_KEY'] = os.getenv('LANGCHAIN_API_KEY')
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY')

llm = ChatGroq(model_name = "llama-3.3-70b-versatile", temperature = 0)

class State(TypedDict):
  history: Annotated[Sequence[BaseMessage], add_messages]
  queries: Annotated[List[str]|None, ..., 'List of rewritten questions to query database.']
  context: Annotated[Document|None, ..., 'Document of chunks retrieved from database.']

class Router(BaseModel):
  path: Literal['chatbot', 'rewrite', 'human']

structured_llm_router = llm.with_structured_output(Router)

def route_question(state: State):
  prompt_route = ChatPromptTemplate.from_template(template_route.content)
  if state['history']:
    question = state['history'][-1].content
  response = structured_llm_router.invoke(prompt_route.format(question = question))
  if response.path == 'chatbot':
    return 'chatbot'
  elif response.path == 'rewrite':
    return 'rewrite'
  else:
    return 'human'

def webtool(state: State):
  '''This function acts as a wrapper to tavilytoolsearch and return a ToolMessage stored in 'history' key. '''
  llm_response = state['history'][-1] 
  add_kwargs = llm_response.additional_kwargs['tool_calls'][0]
  query = add_kwargs['function']['arguments']
  # Convert jsonstring into dict and extract query value
  query = json.loads(query)
  query = query['query']
  tool_response = tavily_tool.invoke(query)
  tool_response = '\n'.join(str(value) for resp in tool_response for value in resp.values())
  return {'history': [ToolMessage(content = tool_response, additional_kwargs = add_kwargs, tool_call_id = add_kwargs['id'])]} 

llm_with_websearch = llm.bind_tools([tavily_tool])

def chat_with_websearch(state: State):
  last_message = state['history'][-1]
  if isinstance(last_message, ToolMessage):
    query = last_message.additional_kwargs['function']['arguments']
    query = json.loads(query) # Convert jsonstring to dict type.
    query = query['query']
    context = last_message.content
    prompt_response = ChatPromptTemplate.from_template(template_response.content)
    response = llm_with_websearch.invoke(prompt_response.format(question = query, context = context))
    if response.content == '': # This check prevents infinite loop if the webtool can't make up an answer.
      response.content = "I'm sorry, I can't answer to this question right now. Try with another question."
    return {'history': [response]}
  response = llm_with_websearch.invoke(last_message.content)
  return {'history': [response]}

def conditional_tool(state: State):
  answer = state['history'][-1]
  if 'tool_calls' in answer.additional_kwargs and answer.content == '':
    return 'tools'
  else: 
    return END

def rewrite_query(state: State):
  prompt_queries = ChatPromptTemplate.from_template(template_queries.content)
  question = state['history'][-1].content
  queries = llm.invoke(prompt_queries.format(question = question))
  print(queries)
  queries = queries.content
  return {'queries': queries.split('\n')}

def retrieve_context(state: State):
  queries = state['queries']
  # Retrieving chunks for each query and concatenate them into a single string.
  retrieved_chunks = '\n'.join(vector_store.similarity_search(q)[i].page_content for q in queries for i in range(len(vector_store.similarity_search(q))))
  return {'context': Document(page_content= retrieved_chunks)}

def generate_response(state: State):
  prompt_response = ChatPromptTemplate.from_template(template_response_rag.content)
  question = state['history'][-1].content
  context = state['context']
  answer = llm.invoke(prompt_response.format(question = question, context = context))
  return {'history': [answer]}

def human_node(state: State):
  last_question = state['history'][-1].content
  human_response = interrupt({'question': last_question}) 
  return {'history': [AIMessage(content = human_response)]}