"""
Сервис для работы с GPT API
"""

import asyncio
import openai
from typing import Optional

class GPTService:
    def __init__(self, api_key: str):
        """Инициализация сервиса GPT"""
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate_response(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        Генерация ответа через GPT

        Args:
            prompt: Пользовательский запрос
            system_prompt: Системный промпт

        Returns:
            Ответ от GPT или None в случае ошибки
        """
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            import os
            model = os.getenv("OPENAI_MODEL", "gpt-4o")

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Ошибка при обращении к GPT: {e}")
            return None

    async def evaluate_response(self, response: str, evaluation_prompt: str) -> Optional[str]:
        """
        Оценка качества ответа

        Args:
            response: Ответ для оценки
            evaluation_prompt: Промпт для оценки

        Returns:
            Оценка от GPT или None в случае ошибки
        """
        full_prompt = f"{evaluation_prompt}\n\nОтвет для оценки:\n{response}"
        return await self.generate_response(full_prompt)

# Глобальный экземпляр сервиса (инициализируется с токеном)
gpt_service: Optional[GPTService] = None

def initialize_gpt_service(api_key: str) -> None:
    """Инициализация глобального экземпляра GPT сервиса"""
    global gpt_service
    gpt_service = GPTService(api_key)

async def get_gpt_response(prompt: str, system_prompt: str = None) -> Optional[str]:
    """Удобная функция для получения ответа от GPT"""
    if not gpt_service:
        raise ValueError("GPT сервис не инициализирован. Вызовите initialize_gpt_service() сначала.")

    return await gpt_service.generate_response(prompt, system_prompt)