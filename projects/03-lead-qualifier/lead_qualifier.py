"""
Квалификация лидов для B2B через LLM (DeepSeek).

Скрипт принимает данные заявки с сайта, отправляет в LLM для классификации,
и возвращает структурированный результат: категория лида, обоснование, рекомендация.

Использование:
    python lead_qualifier.py

Интеграция:
    - Как webhook-обработчик (Flask/FastAPI)
    - Как модуль в n8n через Execute Command
    - Как standalone-скрипт для тестирования

Автор: AI-агентство (github.com/vlad5595)
"""

import json
import os
import sys
from datetime import datetime

import requests

# ── Конфигурация ──────────────────────────────────────────────

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-YOUR-KEY-HERE")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# ── System prompt для классификации ───────────────────────────

SYSTEM_PROMPT = """Ты — AI-ассистент отдела продаж B2B-компании.

Твоя задача: проанализировать заявку потенциального клиента и классифицировать лида.

КАТЕГОРИИ:
- hot (горячий): готов к покупке, есть бюджет, срочная потребность, ЛПР
- warm (тёплый): интерес есть, но нет срочности или бюджет не утверждён, возможно не ЛПР
- cold (холодный): просто интересуется, нет конкретики, студент/фрилансер, спам

КРИТЕРИИ ОЦЕНКИ:
1. Должность — ЛПР (директор, руководитель, владелец) = выше приоритет
2. Размер компании — чем больше, тем выше потенциал
3. Бюджет — указан конкретный = горячий сигнал
4. Срочность — «нужно вчера» vs «просто смотрим»
5. Конкретика запроса — детальное ТЗ vs «расскажите что умеете»

Ответь строго в JSON-формате:
{
    "category": "hot" | "warm" | "cold",
    "score": 1-10,
    "reasoning": "Краткое обоснование на русском (2-3 предложения)",
    "recommended_action": "Что делать менеджеру (1 предложение)",
    "response_priority": "immediate" | "same_day" | "next_week"
}

Только JSON, без пояснений, без markdown-обёртки."""

# ── Тестовые заявки ───────────────────────────────────────────

SAMPLE_LEADS = [
    {
        "name": "Алексей Петров",
        "company": "ООО СтройГрупп",
        "position": "Генеральный директор",
        "employees": "50-100",
        "email": "petrov@stroygroup.ru",
        "phone": "+7 (495) 123-45-67",
        "message": "Нужна автоматизация обработки заявок с сайта. Сейчас менеджеры тратят по 3 часа в день на ручную обработку. Бюджет до 150 000₽, хотим запустить в течение месяца.",
    },
    {
        "name": "Мария",
        "company": "",
        "position": "Фрилансер",
        "employees": "1",
        "email": "maria_test@gmail.com",
        "phone": "",
        "message": "Привет, расскажите что вы умеете? Интересно для общего развития.",
    },
    {
        "name": "Дмитрий Козлов",
        "company": "ИП Козлов",
        "position": "Владелец",
        "employees": "5-10",
        "email": "kozlov@mail.ru",
        "phone": "+7 (903) 987-65-43",
        "message": "Думаем внедрить чат-бота для поддержки клиентов. Пока на стадии изучения вариантов, бюджет не определён. Можете прислать примеры работ?",
    },
]

# ── Основная функция ──────────────────────────────────────────


def qualify_lead(lead: dict) -> dict:
    """
    Принимает данные лида, отправляет в DeepSeek для классификации.
    Возвращает dict с категорией, оценкой и рекомендацией.
    """

    # Формируем текст заявки для LLM
    lead_text = f"""ЗАЯВКА С САЙТА:
Имя: {lead.get('name', 'Не указано')}
Компания: {lead.get('company', 'Не указано')}
Должность: {lead.get('position', 'Не указано')}
Размер компании: {lead.get('employees', 'Не указано')} сотрудников
Email: {lead.get('email', 'Не указано')}
Телефон: {lead.get('phone', 'Не указано')}
Сообщение: {lead.get('message', 'Пусто')}"""

    # Запрос к DeepSeek
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": lead_text},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        result_text = data["choices"][0]["message"]["content"]
        result = json.loads(result_text)

        # Добавляем метаданные
        result["lead_name"] = lead.get("name", "Не указано")
        result["lead_company"] = lead.get("company", "Не указано")
        result["processed_at"] = datetime.now().isoformat()

        return result

    except requests.RequestException as e:
        return {"error": f"Ошибка API: {str(e)}", "lead_name": lead.get("name")}
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"Ошибка парсинга ответа: {str(e)}", "lead_name": lead.get("name")}


# ── Форматирование результата ─────────────────────────────────


def format_result(result: dict) -> str:
    """Форматирует результат классификации для вывода в консоль."""

    if "error" in result:
        return f"❌ Ошибка для {result.get('lead_name', '?')}: {result['error']}"

    category_emoji = {"hot": "🔥", "warm": "🟡", "cold": "🔵"}
    priority_text = {
        "immediate": "Связаться немедленно",
        "same_day": "Ответить сегодня",
        "next_week": "Можно на следующей неделе",
    }

    emoji = category_emoji.get(result.get("category", ""), "❓")
    priority = priority_text.get(result.get("response_priority", ""), "Не определено")

    return f"""
{'='*60}
{emoji} {result.get('lead_name', '?')} ({result.get('lead_company', '?')})
{'='*60}
Категория:  {result.get('category', '?').upper()} ({result.get('score', '?')}/10)
Приоритет:  {priority}
Обоснование: {result.get('reasoning', '?')}
Рекомендация: {result.get('recommended_action', '?')}
Обработано: {result.get('processed_at', '?')}
"""


def format_telegram_message(result: dict) -> str:
    """Форматирует результат для отправки в Telegram."""

    if "error" in result:
        return f"❌ Ошибка классификации: {result['error']}"

    category_emoji = {"hot": "🔥", "warm": "🟡", "cold": "🔵"}
    emoji = category_emoji.get(result.get("category", ""), "❓")

    return (
        f"{emoji} <b>Новый лид: {result.get('category', '?').upper()}</b> "
        f"({result.get('score', '?')}/10)\n\n"
        f"Имя: {result.get('lead_name', '?')}\n"
        f"Компания: {result.get('lead_company', '?')}\n\n"
        f"<b>Обоснование:</b> {result.get('reasoning', '?')}\n\n"
        f"<b>Рекомендация:</b> {result.get('recommended_action', '?')}"
    )


# ── Точка входа ───────────────────────────────────────────────


def main():
    print("\n🤖 Квалификация лидов через DeepSeek\n")

    if DEEPSEEK_API_KEY == "sk-YOUR-KEY-HERE":
        print("⚠️  Установите DEEPSEEK_API_KEY:")
        print("   export DEEPSEEK_API_KEY='sk-ваш-ключ'\n")
        print("Запуск с тестовыми данными (без реального API)...\n")

        # Показываем структуру без реального вызова
        for lead in SAMPLE_LEADS:
            print(f"📋 Заявка: {lead['name']} ({lead.get('company', 'Не указано')})")
            print(f"   Сообщение: {lead['message'][:80]}...")
            print()
        return

    for lead in SAMPLE_LEADS:
        print(f"📋 Обработка: {lead['name']}...")
        result = qualify_lead(lead)
        print(format_result(result))


if __name__ == "__main__":
    main()
