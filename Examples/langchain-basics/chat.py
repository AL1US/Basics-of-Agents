from dotenv import load_dotenv

from langchain.chat_models import init_chat_model

from langchain.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

model = init_chat_model(
    model = "mistral-large-latest",
    temperature = 0.1
)

# response = model.invoke("complete this operation -> 5 + 6 - 3 = x. find x")

conversation = [
    SystemMessage("You are a helpful assistant for questions regarding programming"),
    HumanMessage("what is python?"),
    AIMessage("python is an inerpreted programming message"),
    HumanMessage("When was it realesed?")
]

response = model.invoke(conversation)

# print(response)
print(response.content)

# LIVE TIME EXAMPLE
# while True:

#     promt = input("Input your promt -> ")   

#     if promt == "1":
#         print("Exit from programm")
#         break
        
#     for chunk in model.stream(promt):
#         print(chunk.text, end="", flush=True)