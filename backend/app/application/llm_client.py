from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import httpx
import logging
import json

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMChatRequest(BaseModel):
    messages: List[LLMMessage]
    temperature: float = 0.3
    max_tokens: int = 2048
    stream: bool = False


class LLMChatResponse(BaseModel):
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class LLMService:
    def __init__(self):
        url = settings.lm_studio_url.rstrip("/")
        # Eliminar /v1 si existe al final
        if url.endswith("/v1"):
            url = url[:-3]
        self.base_url = url
        self.chat_url = f"{self.base_url}/v1/chat/completions"
        self.models_url = f"{self.base_url}/v1/models"
        self.timeout = 120.0
        logger.info(f"LLM Client inicializado con base_url: {self.base_url}")

    async def get_models(self) -> Dict[str, Any]:
        logger.info(f"Obteniendo modelos de: {self.models_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.models_url)
                logger.info(f"Respuesta de modelos: status {response.status_code}")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP obteniendo modelos: {e.response.status_code}")
                return {"error": f"Error HTTP: {e.response.status_code}"}
            except Exception as e:
                logger.error(f"Error obteniendo modelos: {str(e)}")
                return {"error": str(e)}

    async def is_model_loaded(self) -> bool:
        models_info = await self.get_models()
        if "data" in models_info and len(models_info["data"]) > 0:
            # Si hay modelos disponibles, asumimos que está cargado
            # LM Studio no devuelve el campo 'loaded' en su API
            return True
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        logger.info(f"Enviando chat a: {self.chat_url}")
        logger.debug(f"Messages: {messages}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": "ministral-3-8b-instruct-2512",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            try:
                response = await client.post(self.chat_url, json=payload)
                logger.info(f"Respuesta de chat: status {response.status_code}")
                response.raise_for_status()
                response_data = response.json()
                logger.info(f"Respuesta de LM Studio: {json.dumps(response_data, indent=2) if isinstance(response_data, dict) else str(response_data)}")
                return response_data
            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP en chat: {e.response.status_code} - {e.response.text}")
                return {"error": f"Error HTTP: {e.response.status_code}", "detail": e.response.text}
            except Exception as e:
                logger.error(f"Error en chat: {str(e)}")
                return {"error": str(e)}

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        result = await self.chat(messages, temperature, max_tokens)
        
        if "error" in result:
            raise Exception(result["error"])
        
        choices = result.get("choices", [])
        if choices and len(choices) > 0:
            first_choice = choices[0]
            if first_choice and isinstance(first_choice, dict):
                message = first_choice.get("message")
                if message and isinstance(message, dict):
                    content = message.get("content")
                    if content and isinstance(content, str):
                        return content
        return ""


llm_service = LLMService()
