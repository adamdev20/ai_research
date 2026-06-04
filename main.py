import requests
import os

webhook = os.environ["DISCORD_WEBHOOK"]

requests.post(
    webhook,
    json={
        "content": "🚀 Agent berhasil berjalan!"
    }
)

print("sent")
