import os
from dotenv import load_dotenv
from transformers.modeling_utils import init_empty_weights
from langchain_huggingface import HuggingFaceEmbeddings
from astrapy import DataAPIClient
from langchain_astradb import AstraDBVectorStore
from langchain import hub
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.tools.tavily_search import TavilySearchResults
# Environment settings
load_dotenv()
os.environ['ASTRADB_TOKEN'] = os.getenv('ASTRADB_TOKEN')
os.environ['ASTRA_ENDPOINT'] = os.getenv('ASTRA_ENDPOINT')
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY')
# RAG
# Defining embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# Initialize the client
client_astra = DataAPIClient(os.environ['ASTRADB_TOKEN'])
db = client_astra.get_database_by_api_endpoint(
  os.environ['ASTRA_ENDPOINT']
)
collection_list = db.list_collection_names()
vector_store = AstraDBVectorStore(
    embedding = embeddings,
    api_endpoint = os.environ['ASTRA_ENDPOINT'],
    collection_name = 'company_db',
    token = os.environ['ASTRADB_TOKEN']
    )

def store_documents():
  '''This function splits text file in small chunks, embedds and stores them in an AstraDB database.'''
  paths = ['/content/company_profile.txt', '/content/employee_directory.txt', '/content/product_catalog.txt']
  doclist = [TextLoader(path).load() for path in paths]
  for doc in doclist:
    print('Number of characters: ', len(doc[0].page_content))
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100, add_start_index=True)
  all_splits = text_splitter.split_documents(doclist[0] + doclist[1] + doclist[2])
  _ = vector_store.add_documents(documents=all_splits)
  print('Vector database created.')

if 'company_db' not in collection_list:
  store_documents()

# TOOLS
tavily_tool = TavilySearchResults(max_results=2)