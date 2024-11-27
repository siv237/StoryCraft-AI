from typing import Dict, Any

# Базовые настройки Ollama
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "hf.co/Vikhrmodels/Vikhr-Gemma-2B-instruct-GGUF:latest",
    
    # Параметры генерации
    "generation_params": {
        "temperature": 0.1,      # Креативность генерации (0.0 - 1.0)
        "top_p": 0.9,           # Разнообразие выборки токенов
        "top_k": 40,            # Количество токенов для выборки
        "num_predict": 2000,    # Максимальное количество токенов для генерации
        "stop": ["[/INST]"],    # Стоп-токены
    },
    
    # Параметры подключения
    "connection": {
        "timeout": 300,          # Таймаут запроса в секундах
        "max_retries": 3,       # Максимальное количество попыток
        "retry_delay": 2,       # Задержка между попытками в секундах
        "backoff_factor": 1.5,  # Множитель для увеличения задержки
    },
    
    # Параметры контекста
    "context": {
        "max_context_length": 5,    # Максимальное количество событий в контексте
        "similarity_threshold": 0.7, # Порог схожести фраз
        "max_retries_generation": 3, # Максимальное количество попыток генерации при повторах
    },
    
    # Параметры истории
    "history": {
        "max_history_size": 100,    # Максимальный размер истории
        "trim_size": 50,            # Размер до которого обрезать историю
    }
}

# Настройки промптов
PROMPT_CONFIG = {
    "system_context": """Ты опытный писатель визуальных новелл, специализирующийся на создании 
    эмоциональных и захватывающих историй. Твой стиль отличается глубокой проработкой персонажей,
    детальными описаниями и неожиданными поворотами сюжета.""",
    
    "style_guidelines": {
        "tone": "эмоциональный, захватывающий",
        "pacing": "динамичный",
        "description_style": "детальный, атмосферный",
        "dialog_style": "естественный, характерный",
    }
}

def get_generation_params() -> Dict[str, Any]:
    """Возвращает параметры генерации для текущего запроса"""
    return {
        "temperature": OLLAMA_CONFIG["generation_params"]["temperature"],
        "top_p": OLLAMA_CONFIG["generation_params"]["top_p"],
        "top_k": OLLAMA_CONFIG["generation_params"]["top_k"],
        "num_predict": OLLAMA_CONFIG["generation_params"]["num_predict"],
        "stop": OLLAMA_CONFIG["generation_params"]["stop"],
    }

def get_connection_params() -> Dict[str, Any]:
    """Возвращает параметры подключения"""
    return OLLAMA_CONFIG["connection"]

def get_context_params() -> Dict[str, Any]:
    """Возвращает параметры контекста"""
    return OLLAMA_CONFIG["context"]

def get_history_params() -> Dict[str, Any]:
    """Возвращает параметры истории"""
    return OLLAMA_CONFIG["history"]
