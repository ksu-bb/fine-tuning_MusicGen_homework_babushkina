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
- For genre_tags, always output a list even if only one genre.
"""

def enrich_with_gemini(caption: str, api_key: str, model_name="gemini-1.5-pro") -> dict:
    if not HAS_GEMINI:
        raise ImportError("Install google-generativeai: pip install google-generativeai")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = f"Original caption: \"{caption}\"\n\nConvert to structured JSON:"
    
    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, prompt],
            generation_config={"temperature": 0.1, "max_output_tokens": 512})
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        return None

def load_manifest(path):
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries

def save_json_metadata(entry: dict, enriched: dict, audio_dir: str):
    audio_path = entry.get("audio_path") or entry.get("path")
    if not audio_path:
        audio_path = os.path.join(audio_dir, f"{entry['youtube_id']}.wav")
    json_path = os.path.splitext(audio_path)[0] + ".json"
    
    metadata = {
        "description": enriched.get("description", ""),
        "general_mood": enriched.get("general_mood", ""),
        "genre_tags": enriched.get("genre_tags", []),
        "lead_instrument": enriched.get("lead_instrument", ""),
        "accompaniment": enriched.get("accompaniment", ""),
        "tempo_and_rhythm": enriched.get("tempo_and_rhythm", ""),
        "vocal_presence": enriched.get("vocal_presence", ""),
        "production_quality": enriched.get("production_quality", ""),
        "original_caption": entry.get("caption", "")  
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    return json_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=str, required=True, help="Path to input manifest.jsonl (with audio paths and captions)")
    parser.add_argument("--audio_dir", type=str, default=None, help="Directory where audio files are stored (if paths in manifest are relative)")
    parser.add_argument("--api_key", type=str, required=True, help="Gemini API key")
    parser.add_argument("--limit", type=int, default=None, help="Process only N entries")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between API calls (seconds)")
    parser.add_argument("--output_manifest", type=str, default=None, help="Optional: create a new manifest with only audio paths for training")
    args = parser.parse_args()

    entries = load_manifest(args.manifest)
    if args.limit:
        entries = entries[:args.limit]

    if args.audio_dir is None:
        if entries and ("audio_path" in entries[0] or "path" in entries[0]):
            first_path = entries[0].get("audio_path") or entries[0].get("path")
            args.audio_dir = os.path.dirname(first_path)
        else:
            args.audio_dir = os.path.join(os.path.dirname(args.manifest), "audio")

    os.makedirs(args.audio_dir, exist_ok=True)

    processed = set()
    for entry in entries:
        audio_path = entry.get("audio_path") or entry.get("path")
        if audio_path:
            json_path = os.path.splitext(audio_path)[0] + ".json"
            if os.path.exists(json_path):
                processed.add(entry["youtube_id"])

    out_manifest_fh = None
    if args.output_manifest:
        out_manifest_fh = open(args.output_manifest, 'w', encoding='utf-8')

    try:
        for entry in tqdm(entries):
            vid = entry["youtube_id"]
            if vid in processed:
                continue

            caption = entry.get("caption", "")
            if not caption:
                continue

            enriched = enrich_with_gemini(caption, args.api_key)
            if enriched:
                json_path = save_json_metadata(entry, enriched, args.audio_dir)
                processed.add(vid)

                if out_manifest_fh:
                    audio_path = entry.get("audio_path") or entry.get("path")
                    if not audio_path:
                        audio_path = os.path.join(args.audio_dir, f"{vid}.wav")
                    out_manifest_fh.write(json.dumps({"path": audio_path}, ensure_ascii=False) + '\n')
            else:
                print(f"Failed")

            time.sleep(args.delay)
    finally:
        if out_manifest_fh:
            out_manifest_fh.close()

if __name__ == "__main__":
    main()