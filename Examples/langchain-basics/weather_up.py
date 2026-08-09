import requests
from dotenv import load_dotenv

from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

@dataclass
class Context:
    user_id: str
    
@dataclass
class ResponseFormat:
    summary: str
    temperature_celsius: float
    humidity: float

@tool("get_weather", description='Возвращай информацию о погоде в полученном городе на русском языке', return_direct=False)
def get_weather(city: str):
    response = requests.get(f"https://wttr.in/{city}?format=j1")
    return response.json()

@tool("locate_user", description="look up a user's city based on the context")
def locate_user(runtime: ToolRuntime[Context]):
    match runtime.context.user_id:
        case "QWE":
            return "Moscow"
        case "SAM":
            return "Samara"
        case _:
            return "Moscow"
        
model = init_chat_model("mistral-large-latest")

agent = create_agent(
    model = model,
    tools = [get_weather],
    system_prompt="Ты асистент для просмотра погоды, который очень смешной, постоянно шутит и выдаёт текущее состояние погоды"
)

response = agent.invoke({
    "messages":[
        {"role": "user", "content": "Какая погода сейчас в самаре?"}
    ]
})

print(response["messages"][-1].content)