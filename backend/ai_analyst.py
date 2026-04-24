from __future__ import annotations

import json
from typing import Any

import requests

from backend.config import settings


def _heuristic_analysis(signal: dict[str, Any]) -> str:
    warnings = signal.get("warnings") or []
    return (
        "Análisis heurístico:\n"
        f"- Veredicto del scanner: {signal.get('verdict')}\n"
        f"- Nivel: {signal.get('level')} | Score: {signal.get('score_total')} | Calidad dato: {signal.get('data_quality')}\n"
        f"- Consenso: {signal.get('consensus_label')}\n"
        f"- R/R: {signal.get('rr')} | Stop: {signal.get('stop')} | Objetivo: {signal.get('target')}\n"
        f"- Advertencias: {'; '.join(warnings) if warnings else 'sin advertencias críticas'}\n"
        "- Acción: usar solo como candidato. Validar precio, spread y disponibilidad en Kuspit/SIC antes de operar."
    )


def _prompt(signal: dict[str, Any]) -> str:
    payload = {
        "ticker": signal.get("ticker"),
        "name": signal.get("name"),
        "region": signal.get("region"),
        "sector": signal.get("sector"),
        "level": signal.get("level"),
        "score_total": signal.get("score_total"),
        "score_technical": signal.get("score_technical"),
        "score_macro": signal.get("score_macro"),
        "score_sector": signal.get("score_sector"),
        "score_data": signal.get("score_data"),
        "price": signal.get("price"),
        "support": signal.get("support"),
        "resistance": signal.get("resistance"),
        "stop": signal.get("stop"),
        "target": signal.get("target"),
        "rr": signal.get("rr"),
        "rsi": signal.get("rsi"),
        "ret5": signal.get("ret5"),
        "ret20": signal.get("ret20"),
        "data_quality": signal.get("data_quality"),
        "consensus": signal.get("consensus_label"),
        "sources": signal.get("data_sources"),
        "warnings": signal.get("warnings"),
        "catalysts": signal.get("catalysts"),
        "kuspit_status": signal.get("kuspit_status"),
    }
    return (
        "Actúa como analista bursátil prudente para una cuenta pequeña que opera desde Kuspit/SIC. "
        "No des una orden de compra directa. Evalúa si la señal merece vigilancia, preparación o posible revisión operativa. "
        "Distingue claramente entre fuerza técnica, calidad de datos, riesgo de ejecución y validación pendiente en Kuspit. "
        "Responde en español con secciones: Veredicto, Argumentos, Riesgos, Qué validar en Kuspit, Plan de seguimiento.\n\n"
        f"Datos de la señal:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def analyze_signal(signal: dict[str, Any]) -> str:
    if settings.ai_provider != "openai":
        return _heuristic_analysis(signal)
    if not settings.openai_api_key or not settings.openai_model:
        return "[IA OpenAI no configurada: falta OPENAI_API_KEY u OPENAI_MODEL]"

    try:
        response = requests.post(
            settings.openai_base_url,
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "input": _prompt(signal),
                "max_output_tokens": 900,
            },
            timeout=settings.openai_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if "output_text" in payload:
            return str(payload["output_text"])
        parts: list[str] = []
        for output in payload.get("output", []):
            for content in output.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    parts.append(content.get("text", ""))
        return "\n".join(part for part in parts if part).strip() or "[OpenAI respondió sin texto útil]"
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        body = exc.response.text[:500] if exc.response is not None else ""
        if status == 429:
            return (
                "[IA conectada, pero OpenAI rechazó la solicitud por límite/cuota 429. "
                "Revisa créditos, rate limits o intenta más tarde.]"
            )
        return f"[IA OpenAI no disponible: HTTP {status}. Detalle: {body}]"
    except Exception as exc:
        return f"[IA OpenAI no disponible: {exc}]"
