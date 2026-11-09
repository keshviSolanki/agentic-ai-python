
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv() # aa function thienv ni api load thse atle aaya access kri sakasu


while True:
    query = input("ASK QUESTION : ")

    if query == "q":
        break

    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )

    response = client.responses.create(
        model="openai/gpt-oss-20b",
        input=query
    )

    print("AI Response : ",response.output_text)
