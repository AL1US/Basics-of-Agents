import requests

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool

load_dotenv()

@tool("get_weather", description="return weather information from a given sity", return_direct=False)
def get_weather(city: str):
    response = requests.get(f"https://wttr.in/{city}?format=j1")
    return response.json()

agent = create_agent(
    model = "mistral-large-latest",
    tools = [get_weather],
    system_prompt=" you are a helpful weather assistant, who always cracks jokes and is humorous whle remaining helpful."
)

response = agent.invoke({
    "messages": [
        {"role": "user", "content": "What is the weather like in Samara"}
    ]
})

print(response)
print(response["messages"][-1].content)