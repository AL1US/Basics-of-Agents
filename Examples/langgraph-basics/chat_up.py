import json
from pathlib import Path
from typing import TypedDict, List, Union

from langchain_core.messages import HumanMessage, AIMessage
from langchain_mistralai import ChatMistralAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

DATA_FILE = "data.json"


class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]


llm = ChatMistralAI(model="mistral-large-latest")


def process(state: AgentState) -> AgentState:
    response = llm.invoke(state["messages"])
    print(f"AI: {response.content}")
    return {"messages": [AIMessage(content=response.content)]}


graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()


def load_history() -> list[dict]:
    path = Path(DATA_FILE)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_history(history: list[dict]) -> None:
    with open(Path(DATA_FILE), "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


history = load_history()

user_input = input("Enter: ")
while user_input != "exit":
    history.append({"role": "user", "content": user_input})

    messages = [
        HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"])
        for m in history
    ]
    result = agent.invoke({"messages": messages})
    history.append({"role": "assistant", "content": result["messages"][-1].content})
    save_history(history)

    user_input = input("Enter: ")
