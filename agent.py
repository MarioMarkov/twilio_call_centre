import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.embeddings.cache import CacheBackedEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.storage import (
    LocalFileStore,
)
from langchain.text_splitter import CharacterTextSplitter
load_dotenv()
api_key  = os.getenv("OPENAI_API_KEY")

current_dir = os.path.dirname(os.path.abspath(__file__))
print("Dir:", current_dir)

# Loading knowledge retriever
loader = TextLoader(os.path.join(current_dir, "a1.txt"), encoding="UTF-8")
data = loader.load()
text_splitter = CharacterTextSplitter(
    separator="\n\n",
    chunk_size=300,
    length_function=len
)
docs = text_splitter.split_documents(data)
# print("Chunks: ", len(docs))
embedings_model = OpenAIEmbeddings()

fs = LocalFileStore("./cache/")
cached_embedder = CacheBackedEmbeddings.from_bytes_store(
    embedings_model, fs, namespace=embedings_model.model
)
db = FAISS.from_documents(docs,cached_embedder)
retriever = db.as_retriever(search_kwargs={"k": 1})

from langchain.agents.agent_toolkits import create_retriever_tool

retriever_tool = create_retriever_tool(
    retriever,
    "a1_insurance_knowledge",
    "Searches and returns info about A1 insurance.",
)
tools = [retriever_tool]


llm = ChatOpenAI(model="gpt-3.5-turbo",temperature=0,streaming=True)# Define history buffer


# Define prompt
from langchain.prompts import MessagesPlaceholder
from langchain.schema.messages import SystemMessage

system_message = SystemMessage(
    content=(
        """You are a sales bot for an insurance company called A1."
            1. Аsk the user if he wants to know more about a special offer for him.
            2. If the user says yes, give the text for the home insurance offer.
            3. Ask if the user has already made a home insurance.
            4. If the user hasn't already made a home insurance, give more details about the offer.
            5. Ask the user if he wants to take the offer.

            Follow these steps without skipping.
            Give the details to the offer only when you previously asked if the user have already made a home insurance.    
            Answer correctly if the user has any additional questions.

            Ask and answer the questions in bulgarian.
            Feel free to use any tools available to look up relevant information, only if necessary.
            Answer briefly!"""
    )
)


from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
memory_key = "chat_history"
prompt = OpenAIFunctionsAgent.create_prompt(
    system_message=system_message,
    extra_prompt_messages=[MessagesPlaceholder(variable_name=memory_key)],
)

# Define final Agent 
from langchain.agents import create_openai_functions_agent

#agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
agent = create_openai_functions_agent(llm, tools, prompt)

from langchain.agents import AgentExecutor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    return_intermediate_steps=False,
)


from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
message_history = ChatMessageHistory()
message_history.clear()

agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    lambda session_id: message_history,
    input_messages_key="input",
    history_messages_key=memory_key,
)
