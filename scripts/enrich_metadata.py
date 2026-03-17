import os
import json
import time
import argparse
from tqdm import tqdm

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

SYSTEM_PROMPT = """You are a music metadata expert. Convert the given music description into a structured JSON with these EXACT fields:

{
   "description": "Brief summary of the track (1-2 sentences)",
   "general_mood": "Overall emotional character (3-5 adjectives)",
   "genre_tags": ["list", "of", "genre", "strings"],
   "lead_instrument": "Main melodic instrument",
   "accompaniment": "Supporting instruments and textures",
   "tempo_and_rhythm": "Speed and rhythmic character",
   "vocal_presence": "Description of vocals or 'None'",
   "production_quality": "Recording/mixing characteristics"
}

Rules:
- Return ONLY valid JSON, no markdown, no explanations.
- Keep values concise but descriptive.
- Use English for all field values.
- If info is missing, use "Unknown" or empty list.
"""

def enrich_with_gemini(caption: str, api_key: str, model_name="gemini-pro") -> dict:
    if not HAS_GEMINI:
        raise ImportError("Install google-generativeai: pip install google-generativeai")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = f"Original caption: \"{caption}\"\n\nConvert to structured JSON:"
    
    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, prompt],
            generation_config={"temperature": 0.1}
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        print(f"API Error: {e}")
        return None

def load_manifest(path):
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries

def save_enriched(path, entry):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=str, required=True, help="Path to input manifest.jsonl")
    parser.add_argument("--output", type=str, required=True, help="Path to output enriched.jsonl")
    parser.add_argument("--api_key", type=str, required=True, help="Gemini API key")
    parser.add_argument("--limit", type=int, default=None, help="Process only N entries")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between API calls (seconds)")
    args = parser.parse_args()

    entries = load_manifest(args.manifest)
    if args.limit:
        entries = entries[:args.limit]

    processed = set()
    if os.path.exists(args.output):
        with open(args.output, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    processed.add(item['youtube_id'])
    
    for entry in tqdm(entries):
        vid = entry['youtube_id']
        if vid in processed:
            continue
        
        caption = entry.get('caption', '')
        enriched = enrich_with_gemini(caption, args.api_key)
        
        if enriched:
            output_entry = {**entry, "enriched_metadata": enriched}
            save_enriched(args.output, output_entry)
            processed.add(vid)
        
        time.sleep(args.delay) 

if __name__ == "__main__":
    main()