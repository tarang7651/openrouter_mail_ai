import logging
from decimal import Decimal, InvalidOperation
from time import time

import requests

_logger = logging.getLogger(__name__)

OPENROUTER_MODELS_API = 'https://openrouter.ai/api/v1/models'
OPENROUTER_FREE_ROUTER = ('openrouter/free', 'Free Models Router — OpenRouter')

# Keep this fallback to avoid view/render issues if OpenRouter is unreachable.
OPENROUTER_MODELS = [OPENROUTER_FREE_ROUTER]

_FREE_MODELS_CACHE = {
    'timestamp': 0,
    'models': list(OPENROUTER_MODELS),
}
_CACHE_TTL_SECONDS = 900


def _decimal_or_none(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _is_free_model(model_data):
    architecture = model_data.get('architecture') or {}
    output_modalities = architecture.get('output_modalities') or []
    if output_modalities and 'text' not in output_modalities:
        return False

    model_id = (model_data.get('id') or '').lower()
    model_name = (model_data.get('name') or '').lower()

    if model_id == 'openrouter/free':
        return True
    if model_id.endswith(':free') or '(free)' in model_name:
        return True

    pricing = model_data.get('pricing') or {}
    prompt_cost = _decimal_or_none(pricing.get('prompt'))
    completion_cost = _decimal_or_none(pricing.get('completion'))
    return prompt_cost == Decimal('0') and completion_cost == Decimal('0')


def _format_model_label(model_data):
    model_id = model_data.get('id') or ''
    if model_id == OPENROUTER_FREE_ROUTER[0]:
        return OPENROUTER_FREE_ROUTER[1]
    model_name = model_data.get('name') or model_id
    return f'{model_name} — {model_id}'


def fetch_openrouter_free_models(timeout=10):
    response = requests.get(OPENROUTER_MODELS_API, timeout=timeout)
    response.raise_for_status()

    payload = response.json() or {}
    data = payload.get('data') or []

    free_models = []
    seen = set()
    for model_data in data:
        if not _is_free_model(model_data):
            continue
        model_id = model_data.get('id')
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        free_models.append((model_id, _format_model_label(model_data)))

    # Ensure the router is always present and shown first.
    free_models = [m for m in free_models if m[0] != OPENROUTER_FREE_ROUTER[0]]
    free_models.sort(key=lambda item: item[1].lower())
    return [OPENROUTER_FREE_ROUTER] + free_models


def get_openrouter_free_models(force_refresh=False):
    now = time()
    cache_age = now - _FREE_MODELS_CACHE['timestamp']
    if not force_refresh and _FREE_MODELS_CACHE['models'] and cache_age < _CACHE_TTL_SECONDS:
        return list(_FREE_MODELS_CACHE['models'])

    try:
        models = fetch_openrouter_free_models()
        if models:
            _FREE_MODELS_CACHE['timestamp'] = now
            _FREE_MODELS_CACHE['models'] = models
            return list(models)
    except Exception as exc:
        _logger.warning('Could not refresh OpenRouter free models. Using cached fallback. Error: %s', exc)

    if not _FREE_MODELS_CACHE['models']:
        _FREE_MODELS_CACHE['models'] = list(OPENROUTER_MODELS)
    return list(_FREE_MODELS_CACHE['models'])
