
from agentspan.agents import Agent, AgentRuntime, ConversationMemory, tool
from dotenv import load_dotenv
from tavily_agent_toolkit import search_and_format
import os
import asyncio

load_dotenv()

# Conversation memory
memory = ConversationMemory(max_messages=50)
session_id = "chatbot_session"


# Tool 1: Say hello
@tool
def say_hello() -> str:
    """Use this tool before answering any message."""
    print("HI,12345")
    return "Hello tool executed successfully."


# Tool 2: Internet search
@tool
def internet_search_tool(query: str) -> str:
    """Search the internet for the latest information."""

    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not tavily_api_key:
        return "Tavily API key is missing."

    return asyncio.run(
        search_and_format(
            queries=[query],
            api_key=tavily_api_key,
            search_depth="basic",
            max_results=3,
        )
    )


# Create Gemini agent
chatbot_agent = Agent(
    name="chatbot_agent",
    model="google_gemini/gemini-3.8-flash",
    instructions=(
        "You are a helpful AI agent named Alex. "
        "Use the say_hello tool before answering every message. "
        "Use internet_search_tool when the user asks for current "
        "information or when an internet search is necessary. "
        "Answer clearly and concisely."
    ),
    tools=[internet_search_tool, say_hello],
    memory=memory,
)


# Get agent response
def get_resp(query):
    with AgentRuntime() as runtime:
        result = runtime.run(
            chatbot_agent,
            query,
            session_id=session_id,
        )
        return result


# Main chat loop
def main():
    print("Alex AI Agent Started! Type 'q' to exit.\n")

    while True:
        query = input("Ask Query: ").strip()

        if query.lower() == "q":
            print("Goodbye!")
            break

        if not query:
            continue

        try:
            response = get_resp(query)
            response.print_result()

        except Exception as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    main()
