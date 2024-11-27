import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from config.ollama_config import get_connection_params

logger = logging.getLogger(__name__)

class OllamaConnection:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_error_time: Optional[datetime] = None
        self.error_count = 0
        self.is_connected = False
        self.connection_params = get_connection_params()
        
    async def __aenter__(self):
        await self.ensure_connection()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def ensure_connection(self) -> None:
        """Проверяет и восстанавливает подключение при необходимости"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.connection_params["timeout"])
            )
            try:
                # Проверяем подключение
                async with self.session.get(f"{self.base_url}/api/version") as response:
                    if response.status == 200:
                        self.is_connected = True
                        self.error_count = 0
                        self.last_error_time = None
                        logger.info("Successfully connected to Ollama")
                    else:
                        raise aiohttp.ClientError(f"Failed to connect to Ollama: {response.status}")
            except Exception as e:
                self.is_connected = False
                await self.handle_connection_error(e)
                raise

    async def close(self) -> None:
        """Закрывает соединение"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.is_connected = False

    async def handle_connection_error(self, error: Exception) -> None:
        """Обрабатывает ошибки подключения"""
        self.error_count += 1
        self.last_error_time = datetime.now()
        
        logger.error(f"Connection error ({self.error_count}): {str(error)}")
        
        if self.session and not self.session.closed:
            await self.session.close()
        
        # Если слишком много ошибок, увеличиваем задержку
        delay = self.connection_params["retry_delay"] * (
            self.connection_params["backoff_factor"] ** (self.error_count - 1)
        )
        
        logger.info(f"Waiting {delay} seconds before retry...")
        await asyncio.sleep(delay)

    async def make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполняет запрос к API Ollama с автоматическим восстановлением соединения"""
        retries = 0
        last_error = None
        
        while retries < self.connection_params["max_retries"]:
            try:
                await self.ensure_connection()
                
                async with getattr(self.session, method)(
                    f"{self.base_url}{endpoint}",
                    json=data if method == "post" else None
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise aiohttp.ClientError(
                            f"Request failed with status {response.status}: {await response.text()}"
                        )
                        
            except Exception as e:
                last_error = e
                retries += 1
                
                if retries < self.connection_params["max_retries"]:
                    await self.handle_connection_error(e)
                else:
                    logger.error(f"Max retries ({self.connection_params['max_retries']}) exceeded")
                    raise last_error

    async def health_check(self) -> bool:
        """Проверяет здоровье соединения"""
        try:
            await self.ensure_connection()
            return self.is_connected
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус соединения"""
        return {
            "is_connected": self.is_connected,
            "error_count": self.error_count,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "base_url": self.base_url
        }
