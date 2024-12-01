# ComfyUI API: Отслеживание прогресса генерации

## Мониторинг WebSocket через curl

Самый простой способ отслеживать прогресс генерации изображений через WebSocket API:

```bash
curl -N -s --output - -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" "http://localhost:8188/ws?clientId=test123" | strings |grep "type"
```

### Параметры команды:
- `-N` - отключает буферизацию вывода
- `-s` - тихий режим, без прогресс-бара
- `--output -` - вывод в stdout
- `-H` - HTTP заголовки для WebSocket соединения
- `| strings` - фильтрует бинарные данные, оставляя только текст
- `| grep "type"` - фильтрует сообщения, показывая только строки с типом события

### Типы событий:
- `"type":"status"` - статус очереди
- `"type":"execution_start"` - начало генерации
- `"type":"executing"` - выполнение узла
- `"type":"progress"` - прогресс генерации
- `"type":"execution_cached"` - использование кэша
- `"type":"execution_complete"` - завершение генерации
- `"type":"execution_error"` - ошибка генерации

### Пример вывода:

```json
{"type": "status", "data": {"status": {"exec_info": {"queue_remaining": 0}}, "sid": "test123"}}
{"type": "status", "data": {"status": {"exec_info": {"queue_remaining": 1}}}}
{"type": "execution_start", "data": {"prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "execution_cached", "data": {"nodes": [], "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "executing", "data": {"node": "4", "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "executing", "data": {"node": "3", "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "progress", "data": {"value": 1, "max": 50, "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4", "node": "3"}}
{"type": "progress", "data": {"value": 25, "max": 50, "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4", "node": "3"}}
{"type": "progress", "data": {"value": 50, "max": 50, "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4", "node": "3"}}
{"type": "executing", "data": {"node": "8", "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "progress", "data": {"value": 5, "max": 10, "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4", "node": "8"}}
{"type": "progress", "data": {"value": 10, "max": 10, "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4", "node": "8"}}
{"type": "executing", "data": {"node": "9", "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "executed", "data": {"node": "9", "output": {"images": [{"filename": "ComfyUI_00422_.png"}]}, "prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "execution_success", "data": {"prompt_id": "1d054012-d14c-4cbc-bf8a-3707f8755dc4"}}
{"type": "status", "data": {"status": {"exec_info": {"queue_remaining": 0}}}}

### Важные узлы:
- `3` - KSampler (генерация изображения)
- `8` - VAE Decode (декодирование)
- `9` - SaveImage (сохранение результата)
