"""Sanity check: can we reach the LLM configured in .env?"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env and puts its values in os.environ

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)
model = os.environ["LLM_MODEL"]

response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Reply with exactly one word: pong"}],
    temperature=0,
)

print(f"Model:  {model}")
print(f"Answer: {response.choices[0].message.content}")