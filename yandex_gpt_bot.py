#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouGile Automation Bot with Yandex GPT (Extended Version with Human-Readable Reports)
Поддержка: analysis, calendar_sync, governance, sprint_analytics
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import traceback
import requests
from typing import Dict, List, Any, Optional

# Конфигурация
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YOUGILE_API_BASE = "https://ru.yougile.com/api-v2"
API_TIMEOUT = 30
MAX_TOKENS = 4000
TEMPERATURE = 0.1

# Логирование (для Cloud Functions - вывод в stdout)
logger = logging.getLogger("YouGileBot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class PromptManager:
    PROMPTS = {}

    @classmethod
    def load_prompts(cls, filepath: str = "prompts.json") -> None:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cls.PROMPTS = json.load(f)
            logger.info(f"Промпты загружены из {filepath}")
        except Exception as e:
            logger.error(f"Не удалось загрузить промпты: {e}")
            raise

    @classmethod
    def get_prompt(cls, prompt_type: str) -> str:
        if not cls.PROMPTS:
            cls.load_prompts()
        return cls.PROMPTS.get(prompt_type, "")


def extract_json_from_markdown(text: str) -> str:
    """
    Извлекает JSON из markdown-блока кода.
    Удаляет тройные обратные кавычки, язык разметки и комментарии.
    """
    text = text.strip()

    # Убираем markdown обертки через split
    lines = text.split('\n')

    # Удаляем первую строку если она содержит ```
    if lines and lines[0].strip().startswith('```'):
        lines = lines[1:]

    # Удаляем последнюю строку если она содержит ```
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]

    text = '\n'.join(lines)

    # Удаляем JavaScript-style комментарии //
    cleaned_lines = []
    for line in text.split('\n'):
        if '//' in line:
            line = line[:line.find('//')]
        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    return text.strip()


def format_human_readable_report(analysis_data: Dict[str, Any], request_type: str) -> str:
    """
    Преобразует JSON-ответ в человеко-читаемый текстовый отчёт.
    """
    if request_type == "sprint_analytics" or request_type == "sprint":
        return format_sprint_report(analysis_data)
    elif request_type == "analysis":
        return format_analysis_report(analysis_data)
    elif request_type == "governance":
        return format_governance_report(analysis_data)
    elif request_type == "calendar_sync":
        return format_calendar_report(analysis_data)
    else:
        return json.dumps(analysis_data, ensure_ascii=False, indent=2)


def format_sprint_report(data: Dict[str, Any]) -> str:
    """
    Форматирует отчёт по спринту в читаемый вид.
    """
    summary = data.get("executive_summary", {})
    flow = data.get("flow_metrics", {})
    team = data.get("team_performance", {})
    actions = data.get("actionable_recommendations", {})

    report = f"""
╔══════════════════════════════════════════════════════════════╗
║          📊 ОТЧЁТ ПО СПРИНТУ - ФИТОGUIDE                    ║
╚══════════════════════════════════════════════════════════════╝

📅 Дата анализа: {data.get('analysis_metadata', {}).get('analysis_date', 'не указана')}
🎯 Здоровье спринта: {summary.get('sprint_health_score', 'N/A')}/100
📈 Статус: {summary.get('overall_status', 'не определён').upper()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 ДОСТИЖЕНИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    for achievement in summary.get('key_achievements', []):
        report += f"  ✓ {achievement}\n"

    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  КРИТИЧЕСКИЕ РИСКИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    for risk in summary.get('critical_risks', []):
        report += f"  ⚡ {risk}\n"

    # Метрики производительности
    burn_down = flow.get('burn_down', {})
    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 МЕТРИКИ ВЫПОЛНЕНИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Запланировано:  {burn_down.get('planned_sp', 'N/A')} Story Points
  Выполнено:      {burn_down.get('actual_sp', 'N/A')} Story Points
  Осталось:       {burn_down.get('remaining_sp', 'N/A')} Story Points
  Процент:        {burn_down.get('completion_percentage', 'N/A')}%

  Производительность команды: {team.get('velocity_analysis', {}).get('current_velocity', 'N/A')} SP
  Скорость потока: {flow.get('cumulative_flow', {}).get('throughput', 'N/A')} задач/день
  Среднее время выполнения: {flow.get('cycle_time_analysis', {}).get('average_cycle_time', 'N/A')} дней

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 АНАЛИЗ НАГРУЗКИ КОМАНДЫ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    workload = team.get('workload_distribution', {})

    if workload.get('overloaded_members'):
        report += "\n  🔴 ПЕРЕГРУЖЕНЫ:\n"
        for member in workload.get('overloaded_members', []):
            report += f"    • {member.get('member')} ({member.get('role')})\n"
            report += f"      Нагрузка: {member.get('current_load_sp')} SP (норма: {member.get('recommended_load_sp')} SP)\n"
            report += f"      Перегрузка: {int((member.get('load_ratio', 1) - 1) * 100)}%\n"

    if workload.get('underutilized_members'):
        report += "\n  🟢 ОПТИМАЛЬНАЯ НАГРУЗКА:\n"
        for member in workload.get('underutilized_members', []):
            report += f"    • {member.get('member')} ({member.get('role')}) - {member.get('current_load_sp')} SP\n"

    # Узкие места
    bottlenecks = flow.get('cumulative_flow', {}).get('bottlenecks', [])
    if bottlenecks:
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚧 УЗКИЕ МЕСТА В ПРОЦЕССЕ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for bottleneck in bottlenecks:
            report += f"  • Этап: {bottleneck.get('stage')}\n"
            report += f"    Среднее время ожидания: {bottleneck.get('avg_wait_time_days')} дней\n"
            report += f"    Задач в работе: {bottleneck.get('wip_count')}\n"
            report += f"    Причина: {bottleneck.get('evidence')}\n\n"

    # Рекомендации
    immediate = actions.get('immediate_actions', [])
    if immediate:
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 СРОЧНЫЕ ДЕЙСТВИЯ (СДЕЛАТЬ СЕГОДНЯ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for i, action in enumerate(immediate, 1):
            report += f"  {i}. {action.get('action')}\n"
            report += f"     👤 Ответственный: {action.get('owner')}\n"
            report += f"     📅 Дедлайн: {action.get('deadline')}\n"
            report += f"     💡 Эффект: {action.get('expected_impact')}\n\n"

    short_term = actions.get('short_term_improvements', [])
    if short_term:
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 УЛУЧШЕНИЯ НА БЛИЖАЙШИЕ ДНИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for i, improvement in enumerate(short_term, 1):
            report += f"  {i}. {improvement.get('improvement')}\n"
            report += f"     ⏱️  Время внедрения: {improvement.get('implementation_time')}\n"
            report += f"     📈 Эффект: {improvement.get('impact')}\n"
            report += f"     💬 Зачем: {improvement.get('rationale')}\n\n"

    # Темы для ретроспективы
    retro = data.get('retrospective_topics', [])
    if retro:
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗣️  ТЕМЫ ДЛЯ РЕТРОСПЕКТИВЫ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        for i, topic in enumerate(retro, 1):
            report += f"  {i}. {topic.get('topic')}\n"
            report += f"     ❓ Почему важно: {topic.get('why_important')}\n"
            report += f"     🎯 Ожидаемый результат: {topic.get('expected_outcome')}\n\n"

    report += """
╔══════════════════════════════════════════════════════════════╗
║                    КОНЕЦ ОТЧЁТА                             ║
╚══════════════════════════════════════════════════════════════╝
"""

    return report


def format_analysis_report(data: Dict[str, Any]) -> str:
    """
    Форматирует отчёт о созданных задачах.
    """
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║          ✅ ЗАДАЧИ СОЗДАНЫ В YOUGILE                        ║
╚══════════════════════════════════════════════════════════════╝

📊 Статус: {data.get('status', 'не определён').upper()}
✅ Создано задач: {data.get('tasks_created', 0)}
❌ Ошибок: {data.get('tasks_failed', 0)}

"""

    tasks = data.get('tasks', [])
    if tasks:
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += "📝 СОЗДАННЫЕ ЗАДАЧИ\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        for i, task in enumerate(tasks, 1):
            status_icon = "✅" if task.get('status') == 'created' else "❌"
            report += f"{i}. {status_icon} {task.get('title', 'Без названия')}\n"
            if task.get('status') == 'created':
                report += f"   🆔 YouGile ID: {task.get('yougile_id')}\n"
            else:
                report += f"   ⚠️  Ошибка: {task.get('error', 'не указана')}\n"
            report += "\n"

    report += "\n╚══════════════════════════════════════════════════════════════╝\n"
    return report


def format_governance_report(data: Dict[str, Any]) -> str:
    """
    Форматирует отчёт проверки governance.
    """
    return f"""
╔══════════════════════════════════════════════════════════════╗
║          🔍 ПРОВЕРКА СООТВЕТСТВИЯ ПРАВИЛАМ                  ║
╚══════════════════════════════════════════════════════════════╝

Статус проверки: ВЫПОЛНЕНА

{json.dumps(data, ensure_ascii=False, indent=2)}

╚══════════════════════════════════════════════════════════════╝
"""


def format_calendar_report(data: Dict[str, Any]) -> str:
    """
    Форматирует отчёт синхронизации с календарём.
    """
    return f"""
╔══════════════════════════════════════════════════════════════╗
║          📅 СИНХРОНИЗАЦИЯ С КАЛЕНДАРЁМ                      ║
╚══════════════════════════════════════════════════════════════╝

Статус: ВЫПОЛНЕНА

{json.dumps(data, ensure_ascii=False, indent=2)}

╚══════════════════════════════════════════════════════════════╝
"""


def call_yandex_gpt(prompt: str) -> str:
    """
    Вызов Yandex GPT API с использованием нового формата.
    """
    api_key = os.environ.get("YANDEX_API_KEY")
    folder_id = os.environ.get("YANDEX_FOLDER_ID")

    if not api_key:
        logger.error("YANDEX_API_KEY не установлен в переменных окружения")
        raise ValueError("Отсутствует YANDEX_API_KEY")

    if not folder_id:
        logger.error("YANDEX_FOLDER_ID не установлен в переменных окружения")
        raise ValueError("Отсутствует YANDEX_FOLDER_ID")

    model_uri = f"gpt://{folder_id}/yandexgpt-lite/latest"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    json_req = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": TEMPERATURE,
            "maxTokens": str(MAX_TOKENS)
        },
        "messages": [
            {
                "role": "user",
                "text": prompt
            }
        ]
    }

    try:
        logger.info("Отправка запроса к Yandex GPT...")
        response = requests.post(YANDEX_GPT_URL, headers=headers, json=json_req, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Безопасное извлечение текста
        try:
            result = data.get("result", {})
            alternatives = result.get("alternatives", [])
            if alternatives and len(alternatives) > 0:
                message = alternatives[0].get("message", {})
                result_text = message.get("text", "")
            else:
                result_text = ""
                logger.warning("Ответ от Yandex GPT не содержит alternatives")
        except (AttributeError, IndexError, KeyError) as e:
            logger.error(f"Ошибка извлечения текста из ответа GPT: {e}")
            logger.error(f"Структура ответа: {data}")
            raise

        logger.info("Успешный вызов Yandex GPT")
        return result_text

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка при вызове Yandex GPT: {e}")
        logger.error(f"Ответ сервера: {e.response.text if e.response else 'нет ответа'}")
        raise
    except Exception as e:
        logger.error(f"Ошибка вызова Yandex GPT: {e}")
        raise


def create_yougile_task(task_data: Dict[str, Any], column_id: str) -> Dict[str, Any]:
    """
    Создание задачи в YouGile через API.
    """
    api_key = os.environ.get("YOUGILE_API_KEY")
    if not api_key:
        logger.error("YOUGILE_API_KEY не установлен в переменных окружения")
        raise ValueError("Отсутствует YOUGILE_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    task_payload = {
        "title": task_data.get("title", "Новая задача"),
        "description": task_data.get("description", ""),
        "columnId": column_id
    }

    if "assignees" in task_data and task_data["assignees"]:
        task_payload["assigned"] = task_data["assignees"]

    if "tags" in task_data and task_data["tags"]:
        task_payload["tags"] = task_data["tags"]

    url = f"{YOUGILE_API_BASE}/tasks"

    try:
        logger.info(f"Создание задачи в YouGile: {task_payload['title']}")
        response = requests.post(url, headers=headers, json=task_payload, timeout=API_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Задача успешно создана, ID: {result.get('id')}")
        return result
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка при создании задачи в YouGile: {e}")
        logger.error(f"Ответ сервера: {e.response.text if e.response else 'нет ответа'}")
        raise
    except Exception as e:
        logger.error(f"Ошибка создания задачи в YouGile: {e}")
        raise


def process_analysis_request(gpt_response: str) -> Dict[str, Any]:
    """
    Обрабатывает запрос типа 'analysis' - создание задач из запроса.
    """
    column_id = os.environ.get("YOUGILE_COLUMN_ID")

    try:
        clean_json = extract_json_from_markdown(gpt_response)
        logger.info("JSON извлечён из markdown")
        parsed_response = json.loads(clean_json)

        if not column_id:
            logger.warning("YOUGILE_COLUMN_ID не установлен, задачи не будут созданы")
            result = {
                "status": "warning",
                "request_type": "analysis",
                "message": "Задачи проанализированы, но не созданы (не указан YOUGILE_COLUMN_ID)",
                "gpt_analysis": parsed_response,
                "tasks_created": 0,
                "tasks_failed": 0,
                "tasks": []
            }
            result["human_readable_report"] = format_human_readable_report(result, "analysis")
            return result

        created_tasks = []
        epics = parsed_response.get("epics", [])

        for epic in epics:
            tasks = epic.get("tasks", [])
            for task in tasks:
                try:
                    yougile_result = create_yougile_task(task, column_id)
                    created_tasks.append({
                        "task_id": task.get("task_id"),
                        "yougile_id": yougile_result.get("id"),
                        "title": task.get("title"),
                        "status": "created"
                    })
                except Exception as e:
                    logger.error(f"Не удалось создать задачу {task.get('title')}: {e}")
                    created_tasks.append({
                        "task_id": task.get("task_id"),
                        "title": task.get("title"),
                        "status": "failed",
                        "error": str(e)
                    })

        result = {
            "status": "success",
            "request_type": "analysis",
            "tasks_created": len([t for t in created_tasks if t["status"] == "created"]),
            "tasks_failed": len([t for t in created_tasks if t["status"] == "failed"]),
            "tasks": created_tasks,
            "gpt_analysis": parsed_response
        }

        result["human_readable_report"] = format_human_readable_report(result, "analysis")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return {
            "status": "error",
            "request_type": "analysis",
            "message": f"Ошибка парсинга: {e}",
            "raw_response": gpt_response[:500]
        }


def process_other_request(gpt_response: str, request_type: str) -> Dict[str, Any]:
    """
    Обрабатывает запросы типа calendar_sync, governance, sprint_analytics.
    """
    try:
        clean_json = extract_json_from_markdown(gpt_response)
        logger.info(f"JSON извлечён для типа {request_type}")
        parsed_response = json.loads(clean_json)

        # Создаем человеко-читаемый отчёт
        human_readable = format_human_readable_report(parsed_response, request_type)

        messages = {
            "calendar_sync": "Анализ календарной синхронизации выполнен",
            "governance": "Проверка governance правил выполнена",
            "sprint_analytics": "Аналитика спринта выполнена",
            "sprint": "Аналитика спринта выполнена"
        }

        return {
            "status": "success",
            "request_type": request_type,
            "message": messages.get(request_type, "Запрос обработан"),
            "analysis": parsed_response,
            "human_readable_report": human_readable
        }

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга {request_type}: {e}")
        return {
            "status": "error",
            "request_type": request_type,
            "message": f"Ошибка парсинга: {e}",
            "raw_response": gpt_response[:500]
        }


def main(input_data: Dict[str, Any]) -> str:
    """
    Основная логика работы бота.
    """
    try:
        request_type = input_data.get("type", "analysis")
        input_text = input_data.get("text", "")

        if not input_text:
            return json.dumps({
                "status": "error",
                "message": "Отсутствует текст запроса"
            }, ensure_ascii=False)

        prompt_types = {
            "analysis": "analysis",
            "calendar": "calendar_sync",
            "governance": "governance",
            "sprint": "sprint_analytics"
        }

        prompt_key = prompt_types.get(request_type, "analysis")
        prompt = PromptManager.get_prompt(prompt_key)

        if not prompt:
            return json.dumps({
                "status": "error",
                "message": f"Промпт '{prompt_key}' не найден"
            }, ensure_ascii=False)

        full_prompt = f"{prompt}\n\nЗапрос:\n{input_text}\nОтвет:"
        gpt_response = call_yandex_gpt(full_prompt)

        if request_type == "analysis":
            result = process_analysis_request(gpt_response)
        else:
            result = process_other_request(gpt_response, request_type)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка в main: {e}")
        return json.dumps({
            "status": "error",
            "message": f"Ошибка: {e}"
        }, ensure_ascii=False)


def handler(event, context):
    """
    Точка входа для Yandex Cloud Functions.
    """
    try:
        input_data = {}

        if isinstance(event, dict):
            if "body" in event:
                if isinstance(event["body"], str):
                    try:
                        input_data = json.loads(event["body"])
                    except:
                        input_data = {"text": event["body"]}
                else:
                    input_data = event["body"]
            else:
                input_data = event
        elif isinstance(event, str):
            try:
                input_data = json.loads(event)
            except:
                input_data = {"text": event}

        logger.info(f"Получен запрос: {input_data}")
        response_text = main(input_data)
        logger.info("Запрос успешно обработан")

        return {
            "statusCode": 200,
            "body": response_text
        }
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Ошибка в handler: {e}\n{tb}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": str(e)
            }, ensure_ascii=False)
        }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_type = sys.argv[1] if len(sys.argv) > 2 else "analysis"
        test_text = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
        test_data = {"text": test_text, "type": test_type}
    else:
        test_text = input("Текст запроса: ")
        test_type = input("Тип (analysis/calendar/governance/sprint): ") or "analysis"
        test_data = {"text": test_text, "type": test_type}

    print(main(test_data))
