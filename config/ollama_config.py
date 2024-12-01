from typing import Dict, Any
import os
from ast import literal_eval

def get_env_list(key: str, default: list) -> list:
    """Получение списка из переменной окружения"""
    value = os.getenv(key)
    if value:
        try:
            return literal_eval(value)
        except (ValueError, SyntaxError):
            return default
    return default

def get_env_float(key: str, default: float) -> float:
    """Получение float из переменной окружения"""
    try:
        return float(os.getenv(key, default))
    except (ValueError, TypeError):
        return default

def get_env_int(key: str, default: int) -> int:
    """Получение int из переменной окружения"""
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default

# Базовые настройки Ollama
OLLAMA_CONFIG = {
    "base_url": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "model": os.getenv("OLLAMA_MODEL", "gemma2:latest"),
    
    # Параметры генерации
    "generation_params": {
        "temperature": get_env_float("OLLAMA_TEMPERATURE", 0.05),
        "top_p": get_env_float("OLLAMA_TOP_P", 0.9),
        "top_k": get_env_int("OLLAMA_TOP_K", 40),
        "seed": get_env_int("OLLAMA_SEED", 42),
        "num_ctx": get_env_int("OLLAMA_NUM_CTX", 4096),
        "num_predict": get_env_int("OLLAMA_NUM_PREDICT", 5000),
        "stop": get_env_list("OLLAMA_STOP_TOKENS", ["[/INST]"]),
        "repeat_last_n": get_env_int("OLLAMA_REPEAT_LAST_N", 64),
        "repeat_penalty": get_env_float("OLLAMA_REPEAT_PENALTY", 1.1),
        "tfs_z": get_env_float("OLLAMA_TFS_Z", 1),
        "num_threads": get_env_int("OLLAMA_NUM_THREADS", 8)
    },
    
    # Параметры подключения
    "connection": {
        "timeout": get_env_int("OLLAMA_TIMEOUT", 300),
        "max_retries": get_env_int("OLLAMA_MAX_RETRIES", 3),
        "retry_delay": get_env_int("OLLAMA_RETRY_DELAY", 2),
        "backoff_factor": get_env_float("OLLAMA_BACKOFF_FACTOR", 1.5),
    },
    
    # Параметры контекста
    "context": {
        "max_context_length": get_env_int("OLLAMA_MAX_CONTEXT_LENGTH", 5),
        "similarity_threshold": get_env_float("OLLAMA_SIMILARITY_THRESHOLD", 0.7),
        "max_retries_generation": get_env_int("OLLAMA_MAX_RETRIES_GENERATION", 3),
    },
    
    # Параметры истории
    "history": {
        "max_history_size": get_env_int("OLLAMA_MAX_HISTORY_SIZE", 100),
        "trim_size": get_env_int("OLLAMA_TRIM_SIZE", 50),
    }
}

# Настройки промптов
PROMPT_CONFIG = {
    "system_context": os.getenv("SYSTEM_CONTEXT", """Ты опытный писатель визуальных новелл, специализирующийся на создании 
    эмоциональных и захватывающих историй. Твой стиль отличается глубокой проработкой персонажей,
    детальными описаниями и неожиданными поворотами сюжета."""),
    
    "translator_context": os.getenv("TRANSLATOR_CONTEXT", """You are a professional translator. Translate the following text from Russian to English.
    Focus on descriptive elements that would be useful for image generation."""),
    
    "style_guidelines": {
        "tone": "эмоциональный, захватывающий",
        "pacing": "динамичный",
        "description_style": "детальный, атмосферный",
        "dialog_style": "естественный, характерный",
    }
}

def get_generation_params() -> Dict[str, Any]:
    """Возвращает параметры генерации для текущего запроса"""
    return OLLAMA_CONFIG["generation_params"]

def get_connection_params() -> Dict[str, Any]:
    """Возвращает параметры подключения"""
    return OLLAMA_CONFIG["connection"]

def get_context_params() -> Dict[str, Any]:
    """Возвращает параметры контекста"""
    return OLLAMA_CONFIG["context"]

def get_history_params() -> Dict[str, Any]:
    """Возвращает параметры истории"""
    return OLLAMA_CONFIG["history"]
