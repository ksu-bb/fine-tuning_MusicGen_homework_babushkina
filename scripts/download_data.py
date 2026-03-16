import os
import subprocess
import json
import pandas as pd
from datasets import load_dataset

OUTPUT_DIR = "data/audio"
METADATA_DIR = "data/metadata"
NUM_SAMPLES = 50  
DURATION = 10     
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)


dataset = load_dataset("google/MusicCaps", split="train")
samples = dataset.select(range(NUM_SAMPLES))


for i, item in enumerate(samples):
    youtube_id = item['yt_id']
    caption = item['caption']
    output_filename = f"{youtube_id}.wav"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    if os.path.exists(output_path):
        continue

    cmd = [
        "yt-dlp",
        "-x",                    
        "--audio-format", "wav", 
        "--postprocessor-args", f"ffmpeg:-ss 00:00:00 -t {DURATION} -ar 16000 -ac 1", 
        "-o", output_path,       
        f"https://www.youtube.com/watch?v={youtube_id}"]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        meta_path = os.path.join(METADATA_DIR, f"{youtube_id}.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({"yt_id": youtube_id, "raw_caption": caption}, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        continue