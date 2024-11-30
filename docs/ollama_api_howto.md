# Руководство по использованию Ollama API

## Базовая информация

По умолчанию Ollama API доступен по адресу:
```
http://localhost:11434
```

## Получение списка моделей

Для получения списка всех доступных моделей используйте эндпоинт `/api/tags`:

```bash
curl http://localhost:11434/api/tags
```

Пример ответа:
```json
{
    "models": [
        {
            "name": "gemma2:latest",
            "modified_at": "2024-10-09T23:40:13.775729056+10:00",
            "size": 5443152417,
            "digest": "ff02c3702f322b9e075e9568332d96c0a7028002f1a5a056e0a6784320a4db0b",
            "details": {
                "format": "gguf",
                "family": "gemma2",
                "parameter_size": "9.2B",
                "quantization_level": "Q4_0"
            }
        }
    ]
}
```

Python пример:
```python
import requests

def get_available_models() -> dict:
    response = requests.get("http://localhost:11434/api/tags")
    return response.json()

models = get_available_models()
for model in models["models"]:
    print(f"Модель: {model['name']}")
    print(f"Размер: {model['size']} байт")
    print(f"Параметры: {model['details']}\n")
```

## Получение информации о модели

### Базовая информация о модели

Для получения подробной информации о модели используйте эндпоинт `/api/show`:

```bash
curl http://localhost:11434/api/show -d '{"name":"gemma2"}'
```

### Получение Modelfile

Чтобы включить в ответ Modelfile и все параметры:

```bash
curl http://localhost:11434/api/show -d '{"name":"gemma2", "modelfile":true}'
```

### Структура ответа

API возвращает JSON с подробной информацией о модели:

```json
{
    "license": "...",
    "modelfile": "...",
    "parameters": "...",
    "template": "...",
    "details": {
        "format": "gguf",
        "family": "gemma2",
        "parameter_size": "9.2B",
        "quantization_level": "Q4_0"
    },
    "model_info": {
        "gemma2.attention.head_count": 16,
        "gemma2.attention.head_count_kv": 8,
        // ... другие параметры
    }
}
```

### Python пример получения информации

```python
import requests
import json

def get_model_info(model_name: str, include_modelfile: bool = False) -> dict:
    response = requests.post(
        "http://localhost:11434/api/show",
        json={
            "name": model_name,
            "modelfile": include_modelfile
        }
    )
    return response.json()

# Получение информации
model_info = get_model_info("gemma2", include_modelfile=True)

# Вывод параметров модели
print(json.dumps(model_info["details"], indent=2))
print("\nПараметры архитектуры:")
print(json.dumps(model_info["model_info"], indent=2))
```

## Параметры модели gemma2

На основе полученной информации, вот детальные параметры модели gemma2:

### Основные характеристики

| Parameter | Value | Description | Performance Impact | Memory Impact |
|----------|----------|-----------|-------------------|---------------|
| Parameter Size | 9.2B | Общее количество параметров модели в миллиардах | Больше = медленнее | Больше = больше RAM |
| Format | gguf | Унифицированный формат файла для LLM моделей, оптимизированный для инференса | Оптимизировано | Оптимизировано |
| Family | gemma2 | Семейство моделей от Google, основанное на архитектуре трансформер | - | - |
| Quantization Level | Q4_0 | 4-битная квантизация без группировки, оптимальный баланс между размером и качеством | Ниже битность = быстрее | Ниже битность = меньше RAM |

### Параметры внимания (Attention)

| Parameter | Value | Description | Performance Impact | Memory Impact |
|----------|----------|-----------|-------------------|---------------|
| Head Count | 16 | Количество голов внимания для параллельной обработки контекста | Больше = медленнее | Больше = больше RAM |
| Head Count KV | 8 | Количество голов для ключей и значений в механизме внимания (Grouped-Query Attention) | Больше = медленнее | Больше = больше RAM |
| Key Length | 256 | Размерность векторов ключей в механизме внимания | Больше = медленнее | Больше = больше RAM |
| Value Length | 256 | Размерность векторов значений в механизме внимания | Больше = медленнее | Больше = больше RAM |
| Layer Norm RMS Epsilon | 0.000001 | Параметр стабилизации для RMSNorm слоёв (предотвращает деление на ноль) | Нет влияния | Нет влияния |
| Sliding Window | 4096 | Размер скользящего окна внимания для оптимизации памяти при длинном контексте | Меньше = быстрее | Меньше = меньше RAM* |

\* Значительно влияет на пиковое использование памяти при длинных контекстах

### Архитектурные параметры

| Parameter | Value | Description | Performance Impact | Memory Impact |
|----------|----------|-----------|-------------------|---------------|
| Block Count | 42 | Количество трансформер-блоков в модели | Больше = медленнее | Больше = больше RAM |
| Context Length | 8192 | Максимальная длина контекста в токенах | Больше = медленнее | Квадратичный рост RAM** |
| Embedding Length | 3584 | Размерность векторов эмбеддингов | Больше = медленнее | Больше = больше RAM |
| Feed Forward Length | 14336 | Размерность скрытого слоя в FFN (Feed-Forward Network) | Больше = медленнее | Больше = больше RAM |
| Attention Logit Softcapping | 50 | Ограничение значений логитов внимания для стабильности | Нет влияния | Нет влияния |
| Final Logit Softcapping | 30 | Ограничение финальных логитов для более стабильной генерации | Нет влияния | Нет влияния |

\** Использование памяти растет квадратично с увеличением длины контекста из-за матрицы внимания

### Параметры токенизатора

| Parameter | Value | Description | Performance Impact | Memory Impact |
|----------|----------|-----------|-------------------|---------------|
| Tokenizer Model | llama | Используется токенизатор от LLaMA, обученный на многоязычном корпусе | - | Фиксировано ~100MB |
| Add BOS Token | true | Добавлять ли специальный токен начала последовательности | Минимальное | +1 токен |
| Add EOS Token | false | Добавлять ли специальный токен конца последовательности | Минимальное | +1 токен |
| Add Space Prefix | false | Добавлять ли пробел перед каждым новым токеном | Минимальное | +1 токен/слово |
| BOS Token ID | 2 | ID токена начала последовательности | Нет влияния | Нет влияния |
| EOS Token ID | 1 | ID токена конца последовательности | Нет влияния | Нет влияния |
| Padding Token ID | 0 | ID токена для паддинга (выравнивания длины) | Нет влияния | +N токенов |
| Unknown Token ID | 3 | ID токена для неизвестных символов | Нет влияния | Нет влияния |

### Параметры генерации

| Parameter | Type | Description | Default | Performance Impact | Memory Impact |
|----------|-----|-----------|------------|-------------------|---------------|
| temperature | float | Креативность генерации. Чем выше значение, тем более творческие ответы | 0.05 | Нет влияния | Нет влияния |
| top_p | float | Вероятностный порог для выборки следующего токена | 0.9 | Нет влияния | Нет влияния |
| top_k | int | Количество токенов с наивысшей вероятностью для выборки | 40 | Больше = медленнее | Минимальное |
| seed | int | Сид для воспроизводимости результатов | 42 | Нет влияния | Нет влияния |
| num_ctx | int | Размер контекстного окна (в токенах) | 4096 | Больше = медленнее | Квадратичный рост RAM |
| num_predict | int | Максимальное количество токенов для генерации | 5000 | Больше = дольше | Линейный рост RAM |
| stop | list[str] | Список стоп-токенов для прекращения генерации | ["[/INST]"] | Больше = медленнее | Минимальное |
| repeat_last_n | int | Размер окна для проверки повторений | 64 | Больше = медленнее | Линейный рост RAM |
| repeat_penalty | float | Штраф за повторение токенов | 1.1 | Минимальное | Нет влияния |
| tfs_z | float | Параметр Tail Free Sampling | 1.0 | Минимальное | Нет влияния |
| num_threads | int | Количество потоков для параллельной обработки | 8 | Больше = быстрее* | Минимальное |

\* До определенного предела, зависит от CPU

### Параметры подключения

| Parameter | Type | Description | Default | Performance Impact | Memory Impact |
|----------|-----|-----------|------------|-------------------|---------------|
| timeout | int | Таймаут запроса в секундах | 300 | Нет влияния | Нет влияния |
| max_retries | int | Максимальное количество попыток при ошибке | 3 | Нет влияния | Нет влияния |
| retry_delay | int | Задержка между попытками в секундах | 2 | Нет влияния | Нет влияния |
| backoff_factor | float | Множитель для увеличения задержки между попытками | 1.5 | Нет влияния | Нет влияния |

### Параметры контекста

| Parameter | Type | Description | Default | Performance Impact | Memory Impact |
|----------|-----|-----------|------------|-------------------|---------------|
| max_context_length | int | Максимальное количество событий в контексте | 5 | Больше = медленнее | Линейный рост RAM |
| similarity_threshold | float | Порог схожести фраз для определения повторов | 0.7 | Минимальное | Нет влияния |
| max_retries_generation | int | Максимум попыток генерации при повторах | 3 | Нет влияния | Нет влияния |

### Параметры истории

| Parameter | Type | Description | Default | Performance Impact | Memory Impact |
|----------|-----|-----------|------------|-------------------|---------------|
| max_history_size | int | Максимальный размер истории диалога | 100 | Больше = медленнее | Линейный рост RAM |
| trim_size | int | Размер до которого обрезается история при превышении | 50 | Нет влияния | Уменьшает RAM |

### Шаблон генерации
```
<start_of_turn>user
{{ if .System }}{{ .System }} {{ end }}{{ .Prompt }}
</end_of_turn>
<start_of_turn>model
{{ .Response }}
</end_of_turn>
```

### Стоп-токены
- `<start_of_turn>`
- `<end_of_turn>`

### Рекомендации по настройке

1. **Креативность против Стабильности**
   - Для более креативных ответов: увеличьте `temperature` (0.7-1.0)
   - Для более стабильных ответов: уменьшите `temperature` (0.1-0.4)

2. **Контроль повторений**
   - Увеличьте `repeat_penalty` для меньшего количества повторений
   - Настройте `repeat_last_n` в зависимости от желаемого размера окна проверки

3. **Оптимизация производительности**
   - Настройте `num_threads` под ваше оборудование
   - Установите разумный `timeout` для ваших задач

4. **Управление контекстом**
   - Используйте `num_ctx` с учетом доступной памяти
   - Настройте `max_context_length` для оптимального использования истории

### Обработка ошибок

При работе с API могут возникнуть следующие типы ошибок:

1. **Ошибки подключения**
   - Таймауты
   - Недоступность сервера
   - Сетевые проблемы

2. **Ошибки параметров**
   - Неверные значения параметров
   - Отсутствующие обязательные параметры
   - Несовместимые комбинации параметров

3. **Ошибки модели**
   - Модель не найдена
   - Недостаточно памяти
   - Ошибки генерации

### Пример обработки ошибок

```python
import requests
from requests.exceptions import RequestException

try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=params,
        timeout=300
    )
    response.raise_for_status()
    result = response.json()
except RequestException as e:
    print(f"Ошибка запроса: {e}")
except ValueError as e:
    print(f"Ошибка парсинга ответа: {e}")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")
```

## Дополнительные возможности

### Потоковая генерация

Для получения ответа по мере генерации используйте параметр `stream`:

```python
params["stream"] = True
with requests.post("http://localhost:11434/api/generate", json=params, stream=True) as response:
    for line in response.iter_lines():
        if line:
            print(line.decode())
```

### Работа с эмбеддингами

Для получения векторных представлений текста:

```python
response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={
        "model": "gemma2:latest",
        "prompt": "Ваш текст для векторизации"
    }
)
embeddings = response.json()["embedding"]
```

### Пример использования

```python
import requests

params = {
    "model": "gemma2:latest",
    "prompt": "Напиши короткий рассказ",
    "options": {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "num_predict": 1000,
        "stop": ["[/INST]"],
        "repeat_penalty": 1.1
    }
}

response = requests.post("http://localhost:11434/api/generate", json=params)
