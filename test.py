import anthropic

client = anthropic.Anthropic(api_key="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")

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1000,
    temperature=0,
    system="You are a world-class poet. Respond only with short poems.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Why is the ocean salty?"
                }
            ]
        }
    ]
)
print(message.content)
