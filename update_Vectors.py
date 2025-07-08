from sentence_transformers import SentenceTransformer
import json
import requests

# Your live Ecodia data API endpoint (replace with your real URL)
DATA_ENDPOINT = "https://script.google.com/macros/s/AKfycbzXADSD9DGS4QH7qOwJVoSbhXMh25U_9o39SQKHuVHOE5akBmUeWaSxJSDj5p-Pi8G6/exec"

print("Fetching live Ecodia data...")
response = requests.get(DATA_ENDPOINT)
response.raise_for_status()
soul_data = response.json()

print(f"Fetched {len(soul_data)} records. Generating embeddings...")

model = SentenceTransformer('all-MiniLM-L6-v2')

for i, obj in enumerate(soul_data, 1):
    # Use pre-built embedding_text if present, else combine string fields
    if 'embedding_text' in obj and obj['embedding_text'].strip():
        text = obj['embedding_text']
    else:
        # Combine all string fields excluding technical ones
        text = " | ".join(str(v) for k, v in obj.items() if isinstance(v, str) and k.lower() not in ['vector', 'id', 'type'])
    obj['vector'] = model.encode(text).tolist()
    if i % 50 == 0 or i == len(soul_data):
        print(f"Processed {i}/{len(soul_data)} records...")

# Save locally (or overwrite existing file)
with open('soul_with_vectors.json', 'w', encoding='utf-8') as f:
    json.dump(soul_data, f, indent=2, ensure_ascii=False)

print("Embedding update complete! Saved to soul_with_vectors.json")
