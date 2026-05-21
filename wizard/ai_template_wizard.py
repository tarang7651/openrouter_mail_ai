import json
import logging
import requests
import html

from lxml import html as lxml_html

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..models.openrouter_const import get_openrouter_free_models

_logger = logging.getLogger(__name__)


TONE_OPTIONS = [
    ('professional', 'Professional'),
    ('casual', 'Casual & Friendly'),
    ('formal', 'Formal'),
    ('persuasive', 'Persuasive'),
    ('empathetic', 'Empathetic'),
    ('urgent', 'Urgent'),
]


class AiTemplateWizard(models.TransientModel):
    _name = 'ai.template.wizard'
    _description = 'AI Email Writer (OpenRouter)'

    source_model = fields.Char()
    source_id = fields.Integer()

    description = fields.Text(
        required=True,
        help='Describe what email you want to generate or rewrite.',
    )
    model_id = fields.Selection(
        selection='_selection_openrouter_models',
        required=True,
    )
    tone = fields.Selection(
        selection=TONE_OPTIONS,
        required=True,
        default='professional',
    )
    include_subject = fields.Boolean(
        default=True,
        help='Generate an improved subject line as well.',
    )

    generated_subject = fields.Char()
    generated_body = fields.Html()
    is_generated = fields.Boolean(default=False)

    tokens_used = fields.Integer(readonly=True)
    model_used = fields.Char(readonly=True)

    @staticmethod
    def _selection_openrouter_models():
        return get_openrouter_free_models()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        configured_model = self.env['ir.config_parameter'].sudo().get_param(
            'openrouter_mail_ai.default_model',
            'openrouter/free',
        )
        allowed_models = {model for model, _label in get_openrouter_free_models()}
        res['model_id'] = configured_model if configured_model in allowed_models else 'openrouter/free'
        return res

    def _get_api_key(self):
        key = self.env['ir.config_parameter'].sudo().get_param('openrouter_mail_ai.api_key')
        if not key or not key.strip():
            raise UserError(_('OpenRouter API key missing. Configure it from Settings.'))
        return key.strip()

    def _build_prompt(self):
        tone_label = dict(TONE_OPTIONS).get(self.tone, 'Professional')
        subject_instruction = (
            'Generate a strong subject line.'
            if self.include_subject
            else 'Keep subject as an empty string.'
        )
        return f"""
You are an expert email copywriter.

Return ONLY valid JSON:
{{
  "subject": "string",
  "body_html": "<p>...</p>"
}}

Rules:
1. Body must be clean HTML suitable for email (no scripts, no style tags).
2. Use clear sections and short paragraphs.
3. Tone: {tone_label}
4. {subject_instruction}
5. If you include links, keep them plain and safe.
6. Do not include markdown fences.

User request:
{(self.description or '').strip()}
""".strip()

    def _call_openrouter(self, prompt):
        api_key = self._get_api_key()
        site_name = self.env['ir.config_parameter'].sudo().get_param(
            'openrouter_mail_ai.site_name',
            'Odoo OpenRouter AI',
        )
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://odoo.com',
                    'X-Title': site_name,
                },
                json={
                    'model': self.model_id,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1800,
                },
                timeout=45,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise UserError(_('AI request timed out. Please try again.'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Could not connect to OpenRouter.'))
        except requests.exceptions.HTTPError as exc:
            try:
                detail = exc.response.json()
            except Exception:
                detail = str(exc)
            raise UserError(_('OpenRouter Error:\n%s') % detail)
        return response.json()

    @staticmethod
    def _remove_wrapper_div(source):
        if source.startswith('<div>') and source.endswith('</div>'):
            return source[5:-6]
        return source

    def _sanitize_html(self, html_source):
        source = (html_source or '').strip()
        if not source:
            return source
        try:
            doc = lxml_html.fromstring(f'<div>{source}</div>')
            for elem in doc.xpath('.//*'):
                for attr in list(elem.attrib):
                    if attr.lower().startswith('on'):
                        del elem.attrib[attr]
                    if elem.attrib.get(attr, '').lower().startswith('javascript:'):
                        del elem.attrib[attr]
            cleaned = lxml_html.tostring(doc, encoding='unicode')
            return self._remove_wrapper_div(cleaned)
        except Exception:
            return source

    def _parse_response(self, data):
        raw = data['choices'][0]['message']['content'].strip()
        if '```' in raw:
            parts = raw.split('```')
            raw = max(parts, key=len).strip()
            if raw.lower().startswith('json'):
                raw = raw[4:].strip()

        try:
            payload = json.loads(raw)
            subject = (payload.get('subject') or '').strip()
            body_html = (payload.get('body_html') or '').strip()
        except Exception:
            subject = ''
            body_html = f"<p>{html.escape(raw)}</p>"

        if not body_html:
            raise UserError(_('AI did not return email HTML content.'))

        return subject, self._sanitize_html(body_html)

    def action_generate(self):
        self.ensure_one()

        prompt = self._build_prompt()
        data = self._call_openrouter(prompt)
        subject, body_html = self._parse_response(data)

        usage = data.get('usage', {})
        self.write({
            'generated_subject': subject,
            'generated_body': body_html,
            'is_generated': True,
            'tokens_used': usage.get('total_tokens', 0),
            'model_used': data.get('model', self.model_id),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_use_email(self):
        self.ensure_one()

        if not self.generated_body:
            raise UserError(_('Please generate an email first.'))

        target = self.env[self.source_model].browse(self.source_id).exists() if self.source_model and self.source_id else False
        if not target:
            raise UserError(_('Source record not found. Please reopen the wizard.'))

        if self.source_model == 'mail.compose.message':
            vals = {'body': self.generated_body}
            if self.include_subject and self.generated_subject:
                vals['subject'] = self.generated_subject
            target.write(vals)
            return {'type': 'ir.actions.act_window_close'}

        if self.source_model == 'mailing.mailing':
            vals = {
                'body_arch': self.generated_body,
                'body_html': self.generated_body,
            }
            if self.include_subject and self.generated_subject:
                vals['subject'] = self.generated_subject
            target.write(vals)
            return {'type': 'ir.actions.act_window_close'}

        raise UserError(_('Unsupported source model: %s') % self.source_model)
