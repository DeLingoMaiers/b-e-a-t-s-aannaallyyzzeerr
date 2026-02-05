# Beat Analyzer для n8n

Анализ аудио через GitHub Actions + Librosa. Возвращает BPM, таймкоды битов и рекомендованные точки склейки.

## Шаг 1: Создать репозиторий

1. Создай новый репозиторий на GitHub (например `beat-analyzer`)
2. Загрузи туда эти файлы:
   ```
   beat-analyzer/
   ├── .github/
   │   └── workflows/
   │       └── analyze-beats.yml
   └── analyze.py
   ```

## Шаг 2: Создать GitHub Token

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token (classic)
3. Выбери scope: `repo` и `workflow`
4. Скопируй токен (покажется только один раз!)

## Шаг 3: Настроить n8n

### Нода 1: Webhook (приём результата)

1. Добавь ноду **Webhook**
2. HTTP Method: `POST`
3. Path: `beats-result` (или любой другой)
4. Скопируй **Production URL** — понадобится дальше

### Нода 2: Запустить анализ (Code)

После ноды где готов трек, добавь **Code** ноду:

```javascript
const track_url = $json.track_url; // URL трека из SUNO
const chat_id = $json.chat_id;
const webhook_url = 'ТВОЙ_WEBHOOK_URL'; // из шага выше

return [{
  json: {
    track_url: track_url,
    chat_id: chat_id,
    job_id: chat_id + '_' + Date.now(),
    webhook_url: webhook_url
  }
}];
```

### Нода 3: HTTP Request (вызов GitHub Action)

- **Method:** POST
- **URL:** `https://api.github.com/repos/ТВОЙ_ЮЗЕР/beat-analyzer/actions/workflows/analyze-beats.yml/dispatches`
- **Headers:**
  - `Authorization`: `Bearer ТВОЙ_GITHUB_TOKEN`
  - `Accept`: `application/vnd.github.v3+json`
- **Body (JSON):**
```json
{
  "ref": "main",
  "inputs": {
    "track_url": "{{ $json.track_url }}",
    "callback_url": "{{ $json.webhook_url }}",
    "job_id": "{{ $json.job_id }}"
  }
}
```

### Нода 4: Wait (опционально)

Добавь паузу 60-90 секунд, чтобы GitHub Action успел выполниться.
Или используй **Wait for Webhook** если хочешь точнее.

### Нода 5: Использовать результат

Webhook вернёт JSON:
```json
{
  "job_id": "123_1699999999",
  "success": true,
  "bpm": 128.5,
  "duration": 180.5,
  "total_beats": 384,
  "beat_times": [0.5, 0.969, 1.438, ...],
  "downbeats": [0.5, 2.375, 4.25, ...],
  "energy_peaks": [45.2, 90.5, 135.8],
  "recommended_cuts": [0.5, 2.375, 4.25, ...]
}
```

**recommended_cuts** — лучшие точки для смены кадра (совпадение бита и начала звука).

## Использование в Shotstack

В промпте для Gemini (Create Shotstack JSON) добавь:

```
══════════════════════════════════════
ТОЧКИ СИНХРОНИЗАЦИИ С МУЗЫКОЙ
══════════════════════════════════════

BPM трека: {{ $json.bpm }}
Рекомендованные точки склейки (в секундах):
{{ $json.recommended_cuts.slice(0, 20).join(', ') }}

ВАЖНО: Каждая смена клипа должна происходить в одну из этих точек!
```

## Лимиты GitHub Actions

- Бесплатно: 2000 минут/месяц
- Один анализ: ~1-2 минуты
- ~1000-2000 треков/месяц бесплатно
