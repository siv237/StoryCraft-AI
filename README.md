# StoryCraft AI

Интерактивная система для создания визуальных новелл с динамической генерацией сюжета и изображений в реальном времени. StoryCraft AI использует потоковую генерацию текста через Ollama и создание изображений через ComfyUI для создания уникального иммерсивного опыта.

## ✨ Ключевые особенности

- 🎭 **Динамическое повествование**
  - Потоковая генерация текста в реальном времени
  - Интерактивные точки выбора для развития сюжета
  - Адаптивные сюжетные линии на основе выборов игрока

- 🎨 **Синхронизированная генерация иллюстраций** (опционально)
  - Автоматическое создание изображений для каждой сцены
  - Согласованность стиля и атмосферы
  - Визуализация ключевых моментов истории

- 🔄 **Реактивный интерфейс**
  - WebSocket коммуникация для мгновенной обратной связи
  - Плавная анимация переходов между сценами
  - Интуитивное управление прогрессом истории

## 📋 Требования

- Python 3.8 или выше
- [Ollama](https://ollama.com/) - обязательно для генерации текста
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - опционально, только для генерации изображений
- Современный веб-браузер с поддержкой WebSocket

> **Note**: ComfyUI требуется только если вы хотите генерировать изображения для сцен. 
> Система будет работать и без ComfyUI, просто пропуская этап генерации изображений.

## 🚀 Установка StoryCraft AI

1. Клонируйте репозиторий:
```bash
git clone https://github.com/siv237/StoryCraft-AI.git
cd StoryCraft-AI
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
.\venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements/dev.txt
```

4. Настройте конфигурацию:
```bash
cp .env.example .env
# Отредактируйте .env под ваши нужды
```

## 🤖 Установка и настройка Ollama (обязательно)

1. Установите Ollama, следуя инструкциям на [официальном сайте](https://ollama.com/)

2. Скачайте модель gemma2:latest:
```bash
ollama pull gemma2:latest
```

3. Проверьте работу Ollama:
```bash
# Проверка версии
ollama --version

# Тест модели
ollama run gemma2:latest "Hello, how are you?"
```

4. Убедитесь, что в вашем .env файле указаны правильные настройки:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma2:latest
```

## 🎨 Установка и настройка ComfyUI (опционально)

1. Клонируйте репозиторий ComfyUI:
```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

2. Создайте виртуальное окружение для ComfyUI:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

3. Установите зависимости ComfyUI:
```bash
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

4. Скачайте необходимые модели:
- Создайте директорию `models/checkpoints`
- Скачайте модель [epicrealism_naturalSinRC1VAE.safetensors](https://civitai.com/models/25694/epicrealism) и поместите в `models/checkpoints`
- Остальные базовые модели будут скачаны автоматически при первом запуске

5. Протестируйте установку:
```bash
python main.py --listen 0.0.0.0 --lowvram --preview-method auto
```

6. Обновите путь к ComfyUI в `.env`:
```
COMFYUI_PATH=/путь/к/вашей/установке/ComfyUI
```

## 🎮 Запуск

1. Запустите Ollama (если не запущен):
```bash
ollama serve
```

2. Запустите ComfyUI (опционально, если нужна генерация изображений):
```bash
cd /путь/к/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --lowvram --preview-method auto
```

3. Запустите StoryCraft AI:
```bash
cd /путь/к/StoryCraft-AI
source venv/bin/activate
python main.py
```

4. Откройте браузер и перейдите по адресу `http://localhost:8000`

## 📚 Документация

В проекте доступна подробная документация:

- **[ALGORITHM.md](ALGORITHM.md)** - Алгоритм работы системы
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Архитектура проекта

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения и создайте коммиты
4. Создайте pull request с описанием изменений
