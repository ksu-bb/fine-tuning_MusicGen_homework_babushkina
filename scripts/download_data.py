import os
import json
from datasets import load_dataset
from tqdm import tqdm
import subprocess
import time
import argparse

def setup_dirs(base_dir):
    os.makedirs(os.path.join(base_dir, "audio"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)

def load_progress(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_progress(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f)

def download_track(yt_id, out_dir, duration=10):
    out_path = os.path.join(out_dir, f"{yt_id}.wav")
    if os.path.exists(out_path):
        return True, out_path
    
    url = f"https://www.youtube.com/watch?v={yt_id}"
    cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--postprocessor-args", f"ffmpeg:-ss 00:00:00 -t 00:00:{duration}",
        "-o", out_path, url]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(out_path):
            return True, out_path
        return False, None
    except Exception as e:
        return False, None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default="/content/drive/MyDrive/musicgen_data")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--duration", type=int, default=10)
    args = parser.parse_args()

    setup_dirs(args.output_dir)
    audio_dir = os.path.join(args.output_dir, "audio")
    manifest_path = os.path.join(args.output_dir, "manifest.jsonl")
    progress_path = os.path.join(args.output_dir, "progress.json")

    downloaded = load_progress(progress_path)
    dataset = load_dataset("google/MusicCaps", split="train")
    subset = dataset.select(range(min(args.limit, len(dataset))))

    existing = set()
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                existing.add(item['youtube_id'])
    
    for i, row in enumerate(tqdm(subset)):
        vid = row['youtube_id']
        if vid in downloaded or vid in existing:
            continue
        
        success, path = download_track(vid, audio_dir, args.duration)
        if success:
            entry = {
                "youtube_id": vid,
                "audio_path": path,
                "caption": row['caption'],
                "aspect_ratio": row.get('aspect_ratio', '')
            }
            with open(manifest_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            downloaded.append(vid)
            existing.add(vid)
            if len(downloaded) % 10 == 0:
                save_progress(progress_path, downloaded)
        time.sleep(1)  

    save_progress(progress_path, downloaded)

if __name__ == "__main__":
    main()