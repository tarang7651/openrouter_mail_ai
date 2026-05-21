import json
import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.openrouter_const import get_openrouter_free_models

_logger = logging.getLogger(__name__)


class AiSubjectWizard(models.TransientModel):
    """
    Bonus feature: Generate 5 subject line variations for a mailing campaign.
    User picks the one they like best with one click.
    """
    _name        = 'ai.subject.wizard'
    _description = 'AI Subject Line Generator (OpenRouter)'

    @staticmethod
    def _selection_openrouter_models():
        return get_openrouter_free_models()

    mailing_id      = fields.Many2one('mailing.mailing', string='Mailing', readonly=True)
    compose_id      = fields.Many2one('mail.compose.message', string='Compose', readonly=True)
    current_subject = fields.Char(string='Current Subject', readonly=True)
    context_hint    = fields.Char(
        string='Campaign context (optional)',
    )
    model_id = fields.Selection(
        selection='_selection_openrouter_models',
        string='AI Model',
        required=True,
    )

    # 5 generated variants
    variant_1 = fields.Char(string='Variant 1', readonly=True)
    variant_2 = fields.Char(string='Variant 2', readonly=True)
    variant_3 = fields.Char(string='Variant 3', readonly=True)
    variant_4 = fields.Char(string='Variant 4', readonly=True)
    variant_5 = fields.Char(string='Variant 5', readonly=True)
    is_generated = fields.Boolean(default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        cfg = self.env['ir.config_parameter'].sudo()
        configured_model = cfg.get_param(
            'openrouter_mail_ai.default_model',
            'openrouter/free',
        )
        allowed_models = {model for model, _label in get_openrouter_free_models()}
        res['model_id'] = configured_model if configured_model in allowed_models else 'openrouter/free'

        compose_id = res.get('compose_id') or self.env.context.get('default_compose_id')
        if compose_id and not res.get('current_subject'):
            compose = self.env['mail.compose.message'].browse(compose_id).exists()
            if compose:
                res['current_subject'] = compose.subject or ''

        mailing_id = res.get('mailing_id') or self.env.context.get('default_mailing_id')
        if mailing_id and not res.get('current_subject'):
            mailing = self.env['mailing.mailing'].browse(mailing_id).exists()
            if mailing:
                res['current_subject'] = mailing.subject or ''

        return res

    def _get_api_key(self):
        key = self.env['ir.config_parameter'].sudo().get_param('openrouter_mail_ai.api_key')
        if not key or not key.strip():
            raise UserError(_(
                'OpenRouter API key is not configured.\n'
                'Go to Settings → General Settings → OpenRouter AI and add your key.\n'
                'Get a free key at https://openrouter.ai/keys'
            ))
        # Strip whitespace and return
        key = key.strip()
        if not key.startswith('sk-or-'):
            _logger.warning(f'API key does not start with expected prefix. Key: {key[:20]}...')
        return key

    def action_generate_subjects(self):
        self.ensure_one()
        api_key = self._get_api_key()

        hint = self.context_hint or self.current_subject or 'a marketing email campaign'
        prompt = f"""
Generate exactly 5 compelling email subject lines for: {hint}

Rules:
- Mix styles: curiosity, urgency, benefit-driven, question, personalised
- Keep each under 60 characters
- No emojis unless naturally fitting
- Return ONLY a raw JSON array of 5 strings. Example: ["Subject 1", "Subject 2", ...]
No explanation, no markdown.
""".strip()

        try:
            resp = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type':  'application/json',
                    'HTTP-Referer':  'https://odoo.com',
                    'X-Title':       'Odoo OpenRouter AI',
                },
                json={
                    'model':    self.model_id,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 400,
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise UserError(_('The AI request timed out. Please try again or choose a faster model.'))
        except requests.exceptions.HTTPError as exc:
            try:
                detail = exc.response.json().get('error', {}).get('message', str(exc))
            except Exception:
                detail = exc.response.text or str(exc)
            
            _logger.error(f'OpenRouter API Error: {exc.response.status_code} - {detail}')
            raise UserError(_('OpenRouter API error: %s\\n\\nPlease check that your API key is valid and your account has credit.') % detail)
        except requests.exceptions.ConnectionError:
            raise UserError(_('Could not reach OpenRouter. Check your internet connection.'))

        raw = resp.json()['choices'][0]['message']['content'].strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()

        try:
            variants = json.loads(raw)
            if not isinstance(variants, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            variants = [line.strip('- ').strip() for line in raw.split('\n') if line.strip()]

        variants = (variants + [''] * 5)[:5]
        self.write({
            'variant_1':    variants[0],
            'variant_2':    variants[1],
            'variant_3':    variants[2],
            'variant_4':    variants[3],
            'variant_5':    variants[4],
            'is_generated': True,
        })

        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'target':    'new',
        }

    def _use_subject(self, subject):
        if subject:
            if self.mailing_id:
                self.mailing_id.write({'subject': subject})
            if self.compose_id:
                self.compose_id.write({'subject': subject})
        return {'type': 'ir.actions.act_window_close'}

    def action_use_variant_1(self): return self._use_subject(self.variant_1)
    def action_use_variant_2(self): return self._use_subject(self.variant_2)
    def action_use_variant_3(self): return self._use_subject(self.variant_3)
    def action_use_variant_4(self): return self._use_subject(self.variant_4)
    def action_use_variant_5(self): return self._use_subject(self.variant_5)
