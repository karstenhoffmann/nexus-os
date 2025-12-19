"""Prompt Registry for LLM calls.

Central management of all prompt templates used in the application.
Prompts can be customized via the Admin UI and are stored in the database.
If no custom prompt exists, the default from this file is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.storage import Storage


@dataclass
class PromptTemplate:
    """A prompt template with metadata."""

    key: str
    category: str
    name: str
    description: str
    template: str
    variables: list[str]
    temperature: float
    max_tokens: int
    is_custom: bool = False


# Default prompts - these are used when no custom prompt is saved in the database
DEFAULT_PROMPTS: dict[str, dict] = {
    "digest_summary": {
        "category": "digest",
        "name": "Digest Zusammenfassung",
        "description": "Generiert Titel, Summary und Highlights aus den geclusterten Themen. "
        "Wird einmal pro Digest aufgerufen, nachdem alle Themen geclustert wurden.",
        "template": """Du bist ein persoenlicher Wissensassistent. Der Nutzer hat diese Woche folgende Themen gelesen:

{topics_joined}

Erstelle:
1. Einen aussagekraeftigen Titel (max 60 Zeichen): Was war das Hauptthema dieser Woche? Der Titel sollte die wichtigsten 2-3 Themen nennen, z.B. "KI-Tools, Produktivitaet & Coding"
2. Eine Zusammenfassung (3-5 Saetze): Was hat den Nutzer diese Woche beschaeftigt?
3. 3-5 Highlights: Die wichtigsten Erkenntnisse oder interessantesten Punkte

Antworte im JSON-Format:
{{
  "title": "...",
  "summary": "...",
  "highlights": ["...", "...", "..."]
}}""",
        "variables": ["topics_joined"],
        "temperature": 0.4,
        "max_tokens": 900,
    },
    "topic_naming_hybrid": {
        "category": "digest",
        "name": "Topic Benennung (Hybrid)",
        "description": "Benennt und fasst einen einzelnen Themen-Cluster zusammen. "
        "Wird fuer jeden Cluster einzeln aufgerufen (Hybrid-Strategie).",
        "template": """Analysiere diese zusammengehoerigen Textauszuege und erstelle:
1. Einen kurzen, praezianten Themennamen (max 4 Worte)
2. Eine Zusammenfassung des Themas (2-3 Saetze)
3. 2-3 Kernpunkte als Liste

Textauszuege:
{samples_joined}

Antworte im JSON-Format:
{{"topic_name": "...", "summary": "...", "key_points": ["...", "..."]}}""",
        "variables": ["samples_joined"],
        "temperature": 0.3,
        "max_tokens": 300,
    },
    "clustering_pure_llm": {
        "category": "digest",
        "name": "Clustering (Pure LLM)",
        "description": "Clustert alle Chunks und benennt Themen in einem einzigen LLM-Call. "
        "Alternative zur Hybrid-Strategie, nutzt mehr Tokens aber weniger API-Calls.",
        "template": """Analysiere diese {chunk_count} Textauszuege und gruppiere sie in {num_clusters} thematische Cluster.

Fuer jeden Cluster:
1. Vergib einen kurzen Themennamen (max 4 Worte)
2. Schreibe eine Zusammenfassung (2-3 Saetze)
3. Liste 2-3 Kernpunkte
4. Liste die Chunk-Indizes (Zahlen in eckigen Klammern)

Textauszuege:
{summaries_text}

Antworte im JSON-Format:
{{
  "clusters": [
    {{
      "topic_name": "...",
      "summary": "...",
      "key_points": ["...", "..."],
      "chunk_indices": [0, 5, 12, ...]
    }},
    ...
  ]
}}""",
        "variables": ["chunk_count", "num_clusters", "summaries_text"],
        "temperature": 0.3,
        "max_tokens": 2000,
    },
}

# Category metadata for UI grouping
PROMPT_CATEGORIES: dict[str, dict] = {
    "digest": {
        "name": "Digest-Generierung",
        "description": "Prompts fuer die Erstellung von Wochen-Digests",
        "icon": "book-open",
    },
    "draft": {
        "name": "Draft-Assistent",
        "description": "Prompts fuer die Erstellung von Textentwuerfen",
        "icon": "edit-3",
        "coming_soon": True,
    },
}


def get_default_prompt(key: str) -> PromptTemplate | None:
    """Get a default prompt template by key."""
    if key not in DEFAULT_PROMPTS:
        return None

    data = DEFAULT_PROMPTS[key]
    return PromptTemplate(
        key=key,
        category=data["category"],
        name=data["name"],
        description=data["description"],
        template=data["template"],
        variables=data["variables"],
        temperature=data["temperature"],
        max_tokens=data["max_tokens"],
        is_custom=False,
    )


def get_prompt(key: str, store: Storage) -> PromptTemplate | None:
    """Get a prompt template, checking for custom version first.

    Args:
        key: The prompt key (e.g., 'digest_summary')
        store: Storage instance to check for custom prompts

    Returns:
        PromptTemplate with either custom or default values,
        or None if the key doesn't exist.
    """
    default = get_default_prompt(key)
    if default is None:
        return None

    # Check for custom prompt in database
    custom = store.get_custom_prompt(key)
    if custom is None:
        return default

    # Merge custom with default (custom overrides template and settings)
    return PromptTemplate(
        key=key,
        category=default.category,
        name=default.name,
        description=default.description,
        template=custom.get("template", default.template),
        variables=default.variables,  # Variables are fixed
        temperature=custom.get("temperature", default.temperature),
        max_tokens=custom.get("max_tokens", default.max_tokens),
        is_custom=True,
    )


def list_prompts(store: Storage) -> list[PromptTemplate]:
    """List all prompts with their current values (custom or default).

    Args:
        store: Storage instance

    Returns:
        List of all PromptTemplates
    """
    prompts = []
    for key in DEFAULT_PROMPTS:
        prompt = get_prompt(key, store)
        if prompt:
            prompts.append(prompt)
    return prompts


def save_prompt(
    key: str,
    template: str,
    temperature: float,
    max_tokens: int,
    store: Storage,
) -> bool:
    """Save a custom prompt to the database.

    Args:
        key: The prompt key
        template: The custom template text
        temperature: LLM temperature setting
        max_tokens: Max tokens for response
        store: Storage instance

    Returns:
        True if saved successfully, False if key doesn't exist
    """
    if key not in DEFAULT_PROMPTS:
        return False

    store.save_custom_prompt(key, template, temperature, max_tokens)
    return True


def reset_prompt(key: str, store: Storage) -> bool:
    """Reset a prompt to its default by removing the custom version.

    Args:
        key: The prompt key
        store: Storage instance

    Returns:
        True if reset successfully, False if key doesn't exist
    """
    if key not in DEFAULT_PROMPTS:
        return False

    store.delete_custom_prompt(key)
    return True


def get_prompts_by_category(store: Storage) -> dict[str, list[PromptTemplate]]:
    """Get all prompts grouped by category.

    Args:
        store: Storage instance

    Returns:
        Dict with category keys and lists of prompts
    """
    prompts = list_prompts(store)
    by_category: dict[str, list[PromptTemplate]] = {}

    for prompt in prompts:
        if prompt.category not in by_category:
            by_category[prompt.category] = []
        by_category[prompt.category].append(prompt)

    return by_category
