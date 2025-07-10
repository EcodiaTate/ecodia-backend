import os
import requests
import json
import time

# === CONFIG ===
DATA_ENDPOINT = "https://script.google.com/macros/s/AKfycbzXADSD9DGS4QH7qOwJVoSbhXMh25U_9o39SQKHuVHOE5akBmUeWaSxJSDj5p-Pi8G6/exec"
OPENAI_KEY = os.environ.get("OPENAI_KEY")

if not OPENAI_KEY:
    raise Exception("OPENAI_KEY environment variable not set! Please set it before running this script.")

EXCLUDED_KEYS = ["vector", "id", "type"]  # Add more if needed

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
processed_count = 0
new_soul_data = []
for i, obj in enumerate(soul_data, 1):
    # Build embedding_text from all non-excluded, non-empty string fields, labeled by header
    fields = [f"{k.capitalize()}: {v.strip()}" for k, v in obj.items()
              if k.lower() not in EXCLUDED_KEYS and isinstance(v, str) and v.strip()]
    if not fields:
        print(f"Skipping record {i} (no content to embed)")
        continue
    embedding_text = " | ".join(fields)
    obj['embedding_text'] = embedding_text
    obj['vector'] = get_openai_embedding(embedding_text)
    new_soul_data.append(obj)
    processed_count += 1
    if processed_count % 10 == 0 or i == len(soul_data):
        print(f"Processed {processed_count}/{len(soul_data)} usable records...")

# === SAVE OUTPUT ===
with open('soul_with_vectors.json', 'w', encoding='utf-8') as f:
    json.dump(new_soul_data, f, indent=2, ensure_ascii=False)

print(f"Embedding update complete! Saved {processed_count} records to soul_with_vectors.json")
