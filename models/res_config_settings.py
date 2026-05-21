from odoo import models, fields
from .openrouter_const import get_openrouter_free_models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @staticmethod
    def _selection_openrouter_models():
        return get_openrouter_free_models()

    openrouter_api_key = fields.Char(
        string='OpenRouter API Key',
        config_parameter='openrouter_mail_ai.api_key',
        help='Get your free API key at https://openrouter.ai/keys',
    )
    openrouter_default_model = fields.Selection(
        selection='_selection_openrouter_models',
        string='Default AI Model',
        config_parameter='openrouter_mail_ai.default_model',
        default='openrouter/free',
        help='This model will be pre-selected when opening the AI generator.',
    )
    openrouter_site_name = fields.Char(
        string='Site / App Name',
        config_parameter='openrouter_mail_ai.site_name',
        default='Odoo OpenRouter AI',
        help='Sent as X-Title to OpenRouter for usage tracking on your dashboard.',
    )
    unsplash_access_key = fields.Char(
        string='Unsplash Access Key',
        config_parameter='openrouter_mail_ai.unsplash_access_key',
        help='Get from https://unsplash.com/developers. Used for dynamic email template images.',
    )
