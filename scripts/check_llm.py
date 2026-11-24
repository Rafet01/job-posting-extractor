"""Sanity check: can we reach the LLM configured in .env?"""

from extractor.llm import get_client, get_default_model

model = get_default_model()
response = get_client().chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Reply with exactly one word: pong"}],
    temperature=0,
)

print(f"Model:  {model}")
print(f"Answer: {response.choices[0].message.content}")
