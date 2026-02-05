import os
import requests
import librosa
import tempfile
import numpy as np

track_url = os.environ['TRACK_URL']
callback_url = os.environ['CALLBACK_URL']
job_id = os.environ['JOB_ID']

print(f"Downloading track: {track_url}")

# Скачиваем трек
response = requests.get(track_url, timeout=120)
response.raise_for_status()

# Определяем расширение
if '.mp3' in track_url.lower():
    suffix = '.mp3'
elif '.wav' in track_url.lower():
    suffix = '.wav'
else:
    suffix = '.mp3'

with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
    f.write(response.content)
    temp_path = f.name

print(f"Analyzing: {temp_path}")

# Загружаем аудио
y, sr = librosa.load(temp_path, sr=22050)
duration = librosa.get_duration(y=y, sr=sr)

print(f"Duration: {duration:.2f}s, Sample rate: {sr}")

# Определяем темп и биты
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

# Округляем до 3 знаков (миллисекунды)
beat_times = [round(t, 3) for t in beat_times]

# Сильные доли (каждый 4-й бит для 4/4)
downbeats = beat_times[::4]

# Находим места с высокой энергией (для drop/climax)
# RMS энергия
rms = librosa.feature.rms(y=y)[0]
rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)

# Находим пики энергии (потенциальные drop'ы)
threshold = np.mean(rms) + np.std(rms) * 1.5
high_energy_frames = np.where(rms > threshold)[0]

# Группируем близкие пики
energy_peaks = []
if len(high_energy_frames) > 0:
    current_group_start = rms_times[high_energy_frames[0]]
    prev_frame = high_energy_frames[0]
    
    for frame in high_energy_frames[1:]:
        if frame - prev_frame > 20:  # Новая группа если разрыв > 20 frames
            energy_peaks.append(round(current_group_start, 2))
            current_group_start = rms_times[frame]
        prev_frame = frame
    
    energy_peaks.append(round(current_group_start, 2))

# Onset detection (начала звуков - более точные точки для склейки)
onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()
onset_times = [round(t, 3) for t in onset_times]

# Рекомендованные точки склейки (совпадение битов и onset'ов ±50ms)
cut_points = []
for beat in beat_times:
    for onset in onset_times:
        if abs(beat - onset) < 0.05:  # ±50ms
            cut_points.append(round(beat, 3))
            break

# Если мало точных совпадений - используем downbeats
if len(cut_points) < 8:
    cut_points = downbeats

# Убираем дубликаты и сортируем
cut_points = sorted(list(set(cut_points)))

result = {
    'job_id': job_id,
    'success': True,
    'bpm': round(float(tempo), 1),
    'duration': round(duration, 2),
    'total_beats': len(beat_times),
    'beat_times': beat_times[:100],  # Первые 100 битов
    'downbeats': downbeats[:30],     # Первые 30 сильных долей
    'energy_peaks': energy_peaks[:10], # До 10 пиков энергии
    'recommended_cuts': cut_points[:50], # До 50 рекомендованных точек склейки
    'analysis': {
        'avg_beat_interval': round(60 / float(tempo), 3) if tempo > 0 else 0,
        'beats_per_bar': 4,
        'time_signature': '4/4'
    }
}

print(f"BPM: {result['bpm']}, Beats: {result['total_beats']}")
print(f"Sending result to: {callback_url}")

# Отправляем результат в n8n
response = requests.post(callback_url, json=result, timeout=30)
print(f"Callback response: {response.status_code}")

# Удаляем временный файл
os.unlink(temp_path)

print("Done!")
