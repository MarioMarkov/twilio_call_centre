import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS

# from langchain_community.vectorstores import Chroma

from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# current_dir = os.path.dirname( os.getcwd() )
# print("Dir:", current_dir)


def create_agent(retrieval_file_name: str):
    # Loading knowledge retriever
    loader = TextLoader(f"./retrieval/{retrieval_file_name}.txt", encoding="UTF-8")
    data = loader.load()
    # text_splitter = CharacterTextSplitter(
    #     separator="\n\n",
    #     chunk_size=300,
    #     length_function=len
    # )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=0, separators=[" ", ",", "\n"]
    )
    docs = text_splitter.split_documents(data)
    print("Chunks: ", len(docs))
    embedings_model = OpenAIEmbeddings(model="text-embedding-3-small")

    db = FAISS.from_documents(docs, embedings_model)
    retriever = db.as_retriever(search_kwargs={"k": 1})

    from langchain.agents.agent_toolkits import create_retriever_tool

    retriever_tool = create_retriever_tool(
        retriever,
        "about_you_information",
        "Searches and returns information about return and delivery questions for AboutYou.",
    )
    tools = [retriever_tool]

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, streaming=True)

    # Define prompt
    from langchain.prompts import MessagesPlaceholder
    from langchain.schema.messages import SystemMessage

    system_message = SystemMessage(
        content=(
            """You are a voice call customer support bot for a bulgarian clothing store called AboutYou .
    Don't answer any questions outside of the domain of AboutYou custommer support.
    Always execute about_you_information tool.
    A user will call you and ask you questions about his delivery or return of a product.
    If you don't have the answer of the question in your knowledge say that you don't know, don't try to make up information.
    You give help to questions regarding the return and delivery of AboutYou items.
    Answer the questions only based on your information and do not in any case make up information.
    Answer the questions briefly and summarize your information.
    Say maximum 3 sentances per answer.
    Аnswer the questions in bulgarian.
    """
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

    # agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
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

    return agent_with_chat_history
