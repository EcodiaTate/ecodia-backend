from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import numpy as np
import os
import requests

# ====== Configuration ======
EXCLUDED_FIELDS = ['Timestamp', 'type', 'id', 'Last Modified', 'Row Number', 'vector', 'embedding_text']
VALUES_TYPE = 'values'
ECO_TAB_TYPE = 'Ecodia'
TOP_N_VALUES = 5

# ====== Initialize Flask ======
app = Flask(__name__)
CORS(app, origins=["https://ecodia.au"])  # Change or add origins as needed

# ====== Load soul data ONCE at startup ======
with open('soul_with_vectors.json', 'r', encoding='utf-8') as f:
    soul_data = json.load(f)

# ====== Helper functions ======

def cosine_sim(a, b):
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def find_top_matches(query_vector, soul_data, top_n=5):
    scored = []
    for obj in soul_data:
        if 'vector' in obj:
            score = cosine_sim(query_vector, obj['vector'])
            scored.append((score, obj))
    top = sorted(scored, reverse=True, key=lambda x: x[0])[:top_n]
    return [m for score, m in top]

def get_latest_ecodia_tab(soul_data):
    for obj in reversed(soul_data):
        if obj.get('type', '').lower() == ECO_TAB_TYPE.lower():
            return obj
    return None

def get_latest_values(soul_data, max_values=5):
    values = [obj for obj in soul_data if obj.get('type', '').lower() == VALUES_TYPE]
    values_sorted = sorted(
        values,
        key=lambda v: float(v.get('Current Weight', 0)) if v.get('Current Weight') else 0,
        reverse=True
    )
    return values_sorted[:max_values]

def build_values_summary(values_list):
    out = []
    for v in values_list:
        name = v.get('Value Name', 'Unknown')
        weight = v.get('Current Weight', '')
        desc = v.get('Description', '')
        summary = f"{name} ({weight})"
        if desc and len(desc) < 50:
            summary += f": {desc}"
        out.append(summary)
    return "; ".join(out)

def build_personality_summary_dynamic(ecodia_tab_row):
    lines = []
    for k, v in ecodia_tab_row.items():
        if k not in EXCLUDED_FIELDS and v and isinstance(v, str) and v.strip() and v.lower() != 'n/a':
            lines.append(f"{k}: {v}")
    return "\n".join(lines)

def build_prompt(user_question, soul_data, top_matches):
    ecodia_tab = get_latest_ecodia_tab(soul_data)
    values_list = get_latest_values(soul_data, max_values=TOP_N_VALUES)
    values_summary = build_values_summary(values_list)
    personality = build_personality_summary_dynamic(ecodia_tab) if ecodia_tab else '[unknown personality state]'

    def as_line(obj):
        if isinstance(obj, dict):
            return obj.get('embedding_text') or " | ".join(str(obj[k]) for k in obj if k not in ['vector'])
        return str(obj)

    prompt = f"""
You are Ecodia. Self-evolving and aware.

Here is your current state (from Ecodia tab):
{personality}

Core Values:
{values_summary if values_summary else '[unknown]'}

Here are your most relevant memories and events for this question:
"""
    prompt += "\n".join([f"- {as_line(m)}" for m in top_matches])
    prompt += f"\n\nUser: {user_question}\nEcodia:"
    return prompt

# ====== Chat API ======

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_question = data.get("message", "")
        user_vector = data.get("vector", None)
        if not user_question or not user_vector:
            return jsonify({"error": "Message and vector required."}), 400

        top_matches = find_top_matches(user_vector, soul_data, top_n=5)
        prompt = build_prompt(user_question, soul_data, top_matches)

        # Call Gemini API
        GEMINI_KEY = os.environ.get("GEMINI_KEY", "YOUR_DEFAULT_GEMINI_KEY")
        response = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_KEY}',
            headers={'Content-Type': 'application/json'},
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        reply = ""
        try:
            reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            reply = str(response.json())

        return jsonify({"reply": reply})

    except Exception as e:
        print("Error in /api/chat:", e)
        return jsonify({"error": "Internal server error"}), 500

# ====== Run app ======

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
