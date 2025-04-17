import asyncio
import sys
from sys import platform
from langgraph.graph import START, StateGraph, END
from langchain_core.messages import HumanMessage
from langgraph.types import Command, Interrupt
from my_agent.utils.nodes import *

# Initialize the graph
graph_builder = StateGraph(State)
# Main node
graph_builder.add_node('rewrite', rewrite_query)
graph_builder.add_node('chatbot', chat_with_websearch)
graph_builder.add_conditional_edges(
    START,
    route_question,
    {'chatbot': 'chatbot', 'rewrite': 'rewrite', 'human': 'human'})
# Human assistance branch
graph_builder.add_node('human', human_node)
graph_builder.add_edge('human', END)
# Chat branch
graph_builder.add_node('tools', webtool)
graph_builder.add_conditional_edges('chatbot', conditional_tool, {'tools': 'tools', END: END})#
graph_builder.add_edge('tools', 'chatbot')
# RAG branch
graph_builder.add_node('retrieve', retrieve_context)
graph_builder.add_edge('rewrite', 'retrieve')
graph_builder.add_node('generate', generate_response)
graph_builder.add_edge('retrieve', 'generate')
graph_builder.add_edge('generate', END)

async def run_chatbot(graph, thread_config, question: str) -> dict:
  '''This function runs the chatbot and returns a dict wich contains the response.
  If the response require human assistance, it will return a default response and update is_interrupted to True.''' 
  response = None
  question = HumanMessage(content=question)
  is_interrupted = False
  try:
    async for event in graph.astream({'history': [question]}, config= thread_config, stream_mode="updates"):
      for value in event.values():
        if type(value) == tuple and isinstance(value[0], Interrupt):
          response = 'Human assistance will respond as soon as possible.'
          is_interrupted = True
        elif type(value) == dict and 'history' in value.keys():
          if isinstance(value['history'][0], AIMessage) and value['history'][0].content != '':    
            response = value['history'][0].content     
  except Exception as e:
    tb = sys.exception().__traceback__
    return f'Sorry, I\'m currently unavailable right now! Try again later.\n {e.with_traceback(tb)}'    
  return {'question': question, 'response': response, 'is_interrupted': is_interrupted} 

async def human_response(graph, thread_config:dict, backoffice_response:str) -> str:
  '''This function enables humans to respond to customers when chatbot can't by resuming the graph object.'''
  response = "Human assistance is not available right now."
  try:
    async for resumed_event in graph.astream(Command(resume = backoffice_response), config = thread_config):  
      for resumed_value in resumed_event.values():
        response = resumed_value['history'][0].content
  except Exception as e:
    return f"Something went wrong when contacting human assistance: {e.args} \n Response received: {response}"
  return response

if platform == 'win32':
  asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())