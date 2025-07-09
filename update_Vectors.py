import os
import requests
import json
import time

# === CONFIG ===
DATA_ENDPOINT = "https://script.google.com/macros/s/AKfycbzXADSD9DGS4QH7qOwJVoSbhXMh25U_9o39SQKHuVHOE5akBmUeWaSxJSDj5p-Pi8G6/exec"
OPENAI_KEY = os.environ.get("OPENAI_KEY")

if not OPENAI_KEY:
    raise Exception("OPENAI_KEY environment variable not set! Please set it before running this script.")

EXCLUDED_KEYS = ["vector", "id", "type"]

# === FETCH DATA ===
print("Fetching live Ecodia data...")
response = requests.get(DATA_ENDPOINT)
response.raise_for_status()
soul_data = response.json()
print(f"Fetched {len(soul_data)} records. Generating embeddings...")

# === HELPER: Get OpenAI embedding ===
def get_openai_embedding(text, retries=3, delay=1):
    for attempt in range(retries):
        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {OPENAI_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "input": text,
                "model": "text-embedding-3-small"
            }
            r = requests.post(url, headers=headers, json=data)
            r.raise_for_status()
            return r.json()['data'][0]['embedding']
        except Exception as e:
            print(f"Error getting embedding, attempt {attempt+1}/{retries}: {e}")
            time.sleep(delay)
    raise Exception(f"Failed to get embedding for text: {text[:60]}...")

# === MAIN LOOP ===
for i, obj in enumerate(soul_data, 1):
    if 'embedding_text' in obj and obj['embedding_text'].strip():
        text = obj['embedding_text']
    else:
        text = " | ".join(
            str(v) for k, v in obj.items() if isinstance(v, str) and k.lower() not in EXCLUDED_KEYS
        )
    obj['vector'] = get_openai_embedding(text)
    if i % 10 == 0 or i == len(soul_data):
        print(f"Processed {i}/{len(soul_data)} records...")

# === SAVE OUTPUT ===
with open('soul_with_vectors.json', 'w', encoding='utf-8') as f:
    json.dump(soul_data, f, indent=2, ensure_ascii=False)

print("Embedding update complete! Saved to soul_with_vectors.json")
