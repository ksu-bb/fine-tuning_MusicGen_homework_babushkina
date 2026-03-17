Fine-tuning MusicGen 

Проект содержит код для дообучения модели MusicGen из репозитория [AudioCraft](https://github.com/facebookresearch/audiocraft) на датасете [MusicCaps](https://huggingface.co/datasets/google/MusicCaps) с обогащёнными метаданными, полученными с помощью LLM (Gemini).

**Структура репозитория:**

- `scripts/` — скрипты для подготовки данных:
  - `download_data.py` — скачивание аудио из YouTube по ссылкам MusicCaps
  - `enrich_metadata.py` — обогащение текстовых описаний
  - `music_dataset.py` — модифицированный файл из AudioCraft
- `configs/` 
  - `train_small.yaml` — конфиг для дообучения модели `musicgen-small`
- `audiocraft/` — подмодуль AudioCraft 
- `requirements.txt` — список зависимостей Python
- `README.md` — данный файл
