import json
import logging
import requests
import base64
import mimetypes
import re
import random

from urllib.parse import urlparse
from uuid import uuid4

from copy import deepcopy
from lxml import html as lxml_html

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..models.openrouter_const import (
    get_openrouter_free_models
)

_logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTS
# =========================================================

TEMPLATE_STYLES = [
    ('promotional', '🎯 Promotional / Sales'),
    ('newsletter', '📰 Newsletter'),
    ('welcome', '👋 Welcome / Onboarding'),
    ('reminder', '⏰ Reminder / Notification'),
    ('educational', '📚 Educational / Tips'),
    ('event', '🎉 Event / Announcement'),
    ('transactional', '📧 Transactional / Receipt'),
    ('feedback', '📋 Feedback / Survey'),
    ('announcement', '📢 Important Announcement'),
]


TONE_OPTIONS = [
    ('professional', '💼 Professional'),
    ('casual', '😊 Casual & Friendly'),
    ('formal', '🏛️ Formal'),
    ('persuasive', '🎯 Persuasive'),
    ('empathetic', '🤝 Empathetic'),
    ('urgent', '⚡ Urgent'),
]


# =========================================================
# CURATED REAL IMAGES
# =========================================================

FALLBACK_IMAGES = {

    'promotional': {

        'hero':
        'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1200&q=80',

        'content':
        'https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=900&q=80',

        'analytics':
        'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=900&q=80',
    },

    'manufacturing': {

        'hero':
        'https://images.unsplash.com/photo-1567789884554-0b844b597180?auto=format&fit=crop&w=1200&q=80',

        'content':
        'https://images.unsplash.com/photo-1581092921461-eab62e97a780?auto=format&fit=crop&w=900&q=80',

        'analytics':
        'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=900&q=80',
    },

    'event': {

        'hero':
        'https://images.unsplash.com/photo-1511578314322-379afb476865?auto=format&fit=crop&w=1200&q=80',

        'content':
        'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=900&q=80',

        'analytics':
        'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?auto=format&fit=crop&w=900&q=80',
    },

    'newsletter': {

        'hero':
        'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80',

        'content':
        'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80',

        'analytics':
        'https://images.unsplash.com/photo-1552664730-d307ca884978?auto=format&fit=crop&w=900&q=80',
    },
}

UNSPLASH_STYLE_QUERIES = {
    'promotional': [
        'business marketing campaign',
        'retail promotion product showcase',
        'sales growth startup office',
    ],
    'newsletter': [
        'editorial newsletter desk',
        'modern office collaboration',
        'business communication creative team',
    ],
    'welcome': [
        'friendly onboarding team welcome',
        'customer success workspace',
        'new user getting started office',
    ],
    'reminder': [
        'calendar planning productivity',
        'professional schedule management',
        'deadline reminder office desk',
    ],
    'educational': [
        'learning workshop training session',
        'online course teaching business',
        'professional education seminar',
    ],
    'event': [
        'conference audience stage',
        'corporate event networking',
        'business announcement event lights',
    ],
    'transactional': [
        'ecommerce payment checkout',
        'digital invoice finance dashboard',
        'online order confirmation',
    ],
    'feedback': [
        'customer interview meeting',
        'survey analytics team discussion',
        'product feedback session office',
    ],
    'announcement': [
        'company update meeting',
        'press release business concept',
        'brand announcement corporate',
    ],
    'manufacturing': [
        'manufacturing production line technology',
        'industrial automation factory',
        'warehouse operations industry',
    ],
}

DESIGN_DIRECTIONS = [
    {
        'name': 'Editorial Grid',
        'layout': 'Asymmetric two-column rhythm with alternating image/text blocks.',
        'palette': 'Muted neutrals with one sharp accent color.',
        'cta': 'Minimal outlined CTA near section transitions.',
        'sections': 'Start with title, then stagger content blocks and finish with a concise footer.',
    },
    {
        'name': 'Bold Campaign',
        'layout': 'Large hero statement, strong section separators, high visual hierarchy.',
        'palette': 'High contrast base with one bright campaign accent.',
        'cta': 'Prominent solid CTA repeated at most twice.',
        'sections': 'Hero, benefit stack, social proof, then closing offer.',
    },
    {
        'name': 'Storytelling Flow',
        'layout': 'Narrative progression from problem to outcome using alternating media blocks.',
        'palette': 'Warm background tones and dark readable typography.',
        'cta': 'Contextual CTA that feels like next step in story.',
        'sections': 'Intro, challenge, solution, result, CTA, footer.',
    },
    {
        'name': 'Product Spotlight',
        'layout': 'Feature-first composition with cards and compact supporting copy.',
        'palette': 'Clean bright canvas with colored feature badges.',
        'cta': 'Button attached to product/feature reveal sections.',
        'sections': 'Spotlight hero, feature rows, comparison/benefit row, CTA, footer.',
    },
    {
        'name': 'Magazine Digest',
        'layout': 'Modular blocks with clear dividers and digest-like scanning flow.',
        'palette': 'Light editorial base with subtle contrast bands.',
        'cta': 'Secondary CTA mid-way, primary CTA at end.',
        'sections': 'Header, highlights, article-like blocks, quick stats, close.',
    },
    {
        'name': 'Minimal Premium',
        'layout': 'Whitespace-heavy, restrained typography, selective imagery.',
        'palette': 'Monochrome base with elegant accent.',
        'cta': 'Single strong CTA near bottom.',
        'sections': 'Calm intro, 2-3 focused value sections, final conversion block.',
    },
    {
        'name': 'Data Story',
        'layout': 'Insight-led sections with metric callouts and supporting imagery.',
        'palette': 'Dark-on-light analytics aesthetic.',
        'cta': 'CTA attached to performance/result section.',
        'sections': 'Headline, metric band, interpretation blocks, action footer.',
    },
]

SNIPPET_ALIASES = {
    's_footer_social': 's_mail_block_footer_social',
    's_header_social': 's_mail_block_header_social',
    's_header_logo': 's_mail_block_header_logo',
}

SNIPPET_VERSION_ATTRS = {
    's_text_block': {'data-vxml': '001'},
    's_title': {'data-vxml': '001'},
    's_cover': {'data-vxml': '001'},
    's_text_image': {'data-vxml': '001'},
    's_image_text': {'data-vxml': '001'},
    's_call_to_action': {'data-vxml': '001'},
    's_picture': {'data-vxml': '001'},
    's_hr': {'data-vxml': '001'},
    's_text_highlight': {'data-vxml': '001'},
    's_mail_block_footer_social': {'data-vxml': '001'},
    's_mail_block_footer_social_left': {'data-vxml': '001'},
    's_mail_block_header_social': {'data-vxml': '001'},
    's_mail_block_header_logo': {'data-vxml': '001'},
}

DEFAULT_EDITOR_SNIPPET = 's_text_block'


# =========================================================
# MAIN MODEL
# =========================================================

class AiStyledTemplateWizard(models.TransientModel):

    _name = 'ai.styled.template.wizard'

    _description = 'AI Email Template Generator'


    # =====================================================
    # FIELDS
    # =====================================================

    source_model = fields.Char()

    source_id = fields.Integer()


    template_style = fields.Selection(
        selection=TEMPLATE_STYLES,
        required=True,
        default='promotional',
    )


    description = fields.Text(
        required=True,
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
    )


    generated_subject = fields.Char()

    generated_body = fields.Html()

    generated_body_raw = fields.Html()

    is_generated = fields.Boolean(
        default=False
    )

    error_message = fields.Char()

    tokens_used = fields.Integer(
        readonly=True
    )

    model_used = fields.Char(
        readonly=True
    )


    # =====================================================
    # MODELS
    # =====================================================

    @staticmethod
    def _selection_openrouter_models():
        return get_openrouter_free_models()


    @api.model
    def default_get(self, fields_list):

        res = super().default_get(fields_list)

        configured_model = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'openrouter_mail_ai.default_model',
            'openrouter/free',
        )

        allowed_models = {
            model
            for model, _label
            in get_openrouter_free_models()
        }

        res['model_id'] = (
            configured_model
            if configured_model in allowed_models
            else 'openrouter/free'
        )

        return res


    # =====================================================
    # HELPERS
    # =====================================================

    def _get_api_key(self):

        key = self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'openrouter_mail_ai.api_key'
        )

        if not key:

            raise UserError(_(
                'OpenRouter API key missing.'
            ))

        return key.strip()


    def _get_site_name(self):

        return self.env[
            'ir.config_parameter'
        ].sudo().get_param(
            'openrouter_mail_ai.site_name',
            'Odoo OpenRouter AI'
        )

    @staticmethod
    def _pick_design_direction():
        direction = random.choice(DESIGN_DIRECTIONS)
        seed = uuid4().hex[:10]
        snippet_candidates = [
            's_title',
            's_cover',
            's_text_block',
            's_image_text',
            's_text_image',
            's_call_to_action',
            's_picture',
            's_text_highlight',
            's_hr',
            's_footer_social',
        ]
        random.shuffle(snippet_candidates)
        selected = snippet_candidates[: random.randint(6, 9)]
        if 's_call_to_action' not in selected:
            selected.append('s_call_to_action')
        if 's_footer_social' not in selected:
            selected.append('s_footer_social')
        return seed, direction, selected


    # =====================================================
    # PROMPT
    # =====================================================

    def _build_prompt(self):

        tone_label = dict(
            TONE_OPTIONS
        ).get(
            self.tone,
            'Professional'
        )

        style_label = dict(
            TEMPLATE_STYLES
        ).get(
            self.template_style,
            'Generic'
        )

        seed, direction, selected_snippets = self._pick_design_direction()
        snippet_line = '\n'.join(
            f'- {snippet}'
            for snippet in selected_snippets
        )

        return f"""
You are an expert Odoo 19 email template designer.

Return STRICTLY one JSON object:

{{
    "subject": "Email Subject",
    "html": "<div>...</div>"
}}

IMPORTANT RULES:

1. Return ONLY valid HTML.

2. DO NOT generate:
    - <odoo>
    - <template>
    - XML
    - QWeb

3. HTML must work directly inside:
    - body_arch
    - body_html

4. Use Odoo mass mailing compatible structure.

5. Use Odoo snippet classes.

6. Use responsive email HTML.

7. NEVER generate image URLs directly.

8. Use placeholders ONLY:
    __HERO_IMAGE__
    __CONTENT_IMAGE__
    __ANALYTICS_IMAGE__

9. Example:
<img src="__HERO_IMAGE__">

10. Keep sections editable.

11. Use sections:
{snippet_line}

12. Every visual block MUST be a snippet section, for example:
<section class="s_text_block ..." data-snippet="s_text_block" data-name="Text">...</section>

13. DO NOT generate these wrappers yourself:
- <html>, <head>, <body>
- <div class="o_layout ...">
- <div class="oe_structure ...">

14. ACCESSIBILITY & READABILITY:
    - Ensure sufficient contrast between text and background
    - Use dark text on light backgrounds or vice versa
    - Avoid similar colors that make text unreadable
    - Use proper padding and spacing for readability
    - If using background images, ALWAYS add a dark overlay behind text

15. ADD CLASS VARIANTS FOR VISUAL DISTINCTIVENESS:
    - For text blocks: add classes like 'text-dark', 'text-muted', or 'bg-light'/'bg-white' as needed
    - Ensure text is clearly readable against background colors

16. COLOR CONTRAST:
    - Maintain approximately WCAG AA readability (target at least 4.5:1 for normal text)
    - Never place dark text on dark backgrounds or light text on light backgrounds

17. DIVERSITY GUARDRAIL (MANDATORY):
    - This output MUST be clearly different from generic "coffee break / default SaaS" templates
    - Avoid repeating this sequence: dark hero -> 3 icon benefits -> testimonial -> repeated CTA
    - Use a fresh layout composition, spacing rhythm, and section order for this run
    - Ensure at least 6 snippet blocks with varied block types

18. APPLY THIS RANDOM CREATIVE BRIEF EXACTLY FOR THIS GENERATION:
    - Diversity Seed: {seed}
    - Direction: {direction['name']}
    - Layout: {direction['layout']}
    - Palette Intent: {direction['palette']}
    - CTA Behavior: {direction['cta']}
    - Section Flow: {direction['sections']}

Return ONLY snippet blocks like <section ... data-snippet="...">...</section>
or compatible snippet div blocks (example: s_hr separator).

Template Style:
{style_label}

Tone:
{tone_label}

Requirements:
{self.description.strip()}

Return ONLY JSON.
""".strip()


    # =====================================================
    # OPENROUTER
    # =====================================================

    def _call_openrouter(self, prompt):

        api_key = self._get_api_key()

        site_name = self._get_site_name()

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
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt,
                        }
                    ],
                    'max_tokens': 3000,
                },

                timeout=45,
            )

            response.raise_for_status()

        except requests.exceptions.Timeout:

            raise UserError(_(
                'AI request timed out.'
            ))

        except requests.exceptions.ConnectionError:

            raise UserError(_(
                'Could not connect to OpenRouter.'
            ))

        except requests.exceptions.HTTPError as exc:

            try:
                detail = exc.response.json()

            except Exception:
                detail = str(exc)

            raise UserError(_(
                'OpenRouter Error:\n%s'
            ) % detail)

        return response.json()


    # =====================================================
    # PARSE AI RESPONSE
    # =====================================================

    def _parse_response(self, data):

        raw = data[
            'choices'
        ][0][
            'message'
        ][
            'content'
        ].strip()

        if '```' in raw:

            parts = raw.split('```')

            raw = max(
                parts,
                key=len
            ).strip()

            if raw.lower().startswith('json'):
                raw = raw[4:].strip()

        try:

            result = json.loads(raw)

        except Exception:

            raise UserError(_(
                'AI returned invalid JSON.'
            ))

        subject = result.get(
            'subject',
            ''
        )

        html = (
            result.get('html')
            or ''
        )

        if not html:

            raise UserError(_(
                'AI did not return HTML.'
            ))

        # Basic sanitization - remove potentially problematic attributes
        try:
            doc = lxml_html.fromstring(f'<div>{html}</div>')
            # Remove inline event handlers
            for elem in doc.xpath('.//*'):
                for attr in list(elem.attrib):
                    if attr.lower().startswith('on'):
                        del elem.attrib[attr]
                    # Remove javascript: URLs
                    if elem.attrib.get(attr, '').lower().startswith('javascript:'):
                        del elem.attrib[attr]
            html = lxml_html.tostring(doc, encoding='unicode')
            # Remove the wrapper div
            if html.startswith('<div>') and html.endswith('</div>'):
                html = html[5:-6]
        except Exception:
            # If sanitization fails, continue with original HTML
            pass

        return subject, html


    # =====================================================
    # INJECT DYNAMIC IMAGES
    # =====================================================

    def _get_unsplash_access_key(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'openrouter_mail_ai.unsplash_access_key',
            ''
        ).strip()

    def _get_style_image_fallback(self):
        return FALLBACK_IMAGES.get(
            self.template_style,
            FALLBACK_IMAGES['promotional']
        )

    def _style_unsplash_query(self):
        queries = UNSPLASH_STYLE_QUERIES.get(
            self.template_style,
            ['business technology office']
        )
        return random.choice(queries)

    @staticmethod
    def _image_url_from_unsplash_photo(photo, width):
        urls = (photo or {}).get('urls') or {}
        raw = (urls.get('raw') or '').strip()
        regular = (urls.get('regular') or '').strip()

        if raw:
            joiner = '&' if '?' in raw else '?'
            return f'{raw}{joiner}auto=format&fit=crop&w={width}&q=80'
        return regular

    def _fetch_unsplash_images(self):
        access_key = self._get_unsplash_access_key()
        if not access_key:
            return {}

        try:
            response = requests.get(
                'https://api.unsplash.com/photos/random',
                headers={
                    'Authorization': f'Client-ID {access_key}',
                    'Accept-Version': 'v1',
                },
                params={
                    'count': 3,
                    'query': self._style_unsplash_query(),
                    'orientation': 'landscape',
                    'content_filter': 'high',
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            _logger.warning('Unsplash fetch failed for style %s: %s', self.template_style, exc)
            return {}

        photos = payload if isinstance(payload, list) else [payload]
        if not photos:
            return {}

        hero_url = self._image_url_from_unsplash_photo(
            photos[0] if len(photos) > 0 else {},
            width=1200,
        )
        content_url = self._image_url_from_unsplash_photo(
            photos[1] if len(photos) > 1 else photos[0],
            width=900,
        )
        analytics_url = self._image_url_from_unsplash_photo(
            photos[2] if len(photos) > 2 else photos[-1],
            width=900,
        )

        return {
            'hero': hero_url,
            'content': content_url,
            'analytics': analytics_url,
        }

    def _inject_real_images(self, html):

        images = self._fetch_unsplash_images()
        fallback = self._get_style_image_fallback()

        html = html.replace(
            '__HERO_IMAGE__',
            images.get('hero') or fallback.get('hero', '')
        )

        html = html.replace(
            '__CONTENT_IMAGE__',
            images.get('content') or fallback.get('content', '')
        )

        html = html.replace(
            '__ANALYTICS_IMAGE__',
            images.get('analytics') or fallback.get('analytics', '')
        )

        return html


    # =====================================================
    # IMAGE ATTACHMENTS
    # =====================================================

    @staticmethod
    def _is_external_image_src(src):
        source = (src or '').strip().lower()
        if not source:
            return False
        if source.startswith(('http://', 'https://')):
            return True
        return False

    @staticmethod
    def _guess_mimetype(url, response):
        content_type = (response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        if content_type.startswith('image/'):
            return content_type

        path = urlparse(url).path or ''
        guessed = mimetypes.guess_type(path)[0] or ''
        if guessed.startswith('image/'):
            return guessed

        return 'image/jpeg'

    def _download_image_to_attachment(self, src_url):
        try:
            response = requests.get(src_url, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            _logger.warning('Failed downloading image URL %s: %s', src_url, exc)
            return False

        content = response.content or b''
        if not content:
            _logger.warning('Image URL returned empty body: %s', src_url)
            return False

        mimetype = self._guess_mimetype(src_url, response)
        if not mimetype.startswith('image/'):
            _logger.warning('URL is not an image content type (%s): %s', mimetype, src_url)
            return False

        path = urlparse(src_url).path or ''
        filename = path.rsplit('/', 1)[-1] if '/' in path else ''
        if not filename:
            extension = mimetypes.guess_extension(mimetype) or '.jpg'
            filename = f'ai_generated{extension}'

        attachment = self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(content),
            'mimetype': mimetype,
            'public': True,
            'res_model': self._name,
            'res_id': self.id,
        })
        return f'/web/image/{attachment.id}'

    def _materialize_external_images(self, html):
        source = (html or '').strip()
        if not source:
            return source

        try:
            wrapper = lxml_html.fromstring(f'<div>{source}</div>')
        except Exception:
            return source

        img_nodes = wrapper.xpath('.//img[@src]')
        if not img_nodes:
            return source

        rewritten_by_src = {}

        for node in img_nodes:
            src = (node.get('src') or '').strip()
            if not self._is_external_image_src(src):
                continue

            if src not in rewritten_by_src:
                rewritten_by_src[src] = self._download_image_to_attachment(src) or src

            node.set('src', rewritten_by_src[src])

        result = lxml_html.tostring(wrapper, encoding='unicode')
        if result.startswith('<div>') and result.endswith('</div>'):
            return result[5:-6]
        return result

    def _disable_preview_click_targets(self, html):
        source = (html or '').strip()
        if not source:
            return source

        try:
            wrapper = lxml_html.fromstring(f'<div>{source}</div>')
        except Exception:
            return source

        for img in wrapper.xpath('.//img'):
            existing_style = (img.get('style') or '').strip()
            click_block_style = (
                'pointer-events:none !important;user-select:none !important;'
                '-webkit-user-drag:none !important;cursor:default !important;'
            )
            img.set('style', f'{existing_style};{click_block_style}' if existing_style else click_block_style)

        for link in wrapper.xpath('.//a[@href]'):
            link.attrib.pop('href', None)
            existing_style = (link.get('style') or '').strip()
            click_block_style = 'pointer-events:none !important;cursor:default !important;text-decoration:none !important;'
            link.set('style', f'{existing_style};{click_block_style}' if existing_style else click_block_style)

        result = lxml_html.tostring(wrapper, encoding='unicode')
        if result.startswith('<div>') and result.endswith('</div>'):
            return result[5:-6]
        return result

    @staticmethod
    def _parse_style_map(style_value):
        parsed = {}
        for chunk in (style_value or '').split(';'):
            if ':' not in chunk:
                continue
            key, value = chunk.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            if key:
                parsed[key] = value
        return parsed

    @staticmethod
    def _style_map_to_string(style_map):
        if not style_map:
            return ''
        return '; '.join(f'{key}: {value}' for key, value in style_map.items())

    @staticmethod
    def _parse_css_color(color_value):
        if not color_value:
            return None
        color_value = color_value.strip().lower()

        if color_value.startswith('#'):
            hex_part = color_value[1:]
            if len(hex_part) == 3:
                try:
                    return tuple(int(c * 2, 16) for c in hex_part)
                except ValueError:
                    return None
            if len(hex_part) == 6:
                try:
                    return tuple(int(hex_part[i:i + 2], 16) for i in (0, 2, 4))
                except ValueError:
                    return None
            return None

        match = re.match(
            r'rgba?\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})(?:\s*,\s*([0-9.]+))?\s*\)',
            color_value,
        )
        if not match:
            return None

        rgb = []
        for index in (1, 2, 3):
            value = max(0, min(255, int(match.group(index))))
            rgb.append(value)
        return tuple(rgb)

    @classmethod
    def _extract_color_from_css_value(cls, css_value):
        if not css_value:
            return None
        match = re.search(
            r'(#[0-9a-fA-F]{3,6}|rgba?\([^)]+\))',
            css_value,
        )
        if not match:
            return None
        return cls._parse_css_color(match.group(1))

    @classmethod
    def _relative_luminance(cls, rgb):
        def _channel(value):
            srgb = value / 255.0
            if srgb <= 0.03928:
                return srgb / 12.92
            return ((srgb + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return (
            0.2126 * _channel(r)
            + 0.7152 * _channel(g)
            + 0.0722 * _channel(b)
        )

    @classmethod
    def _contrast_ratio(cls, rgb_a, rgb_b):
        lum_a = cls._relative_luminance(rgb_a)
        lum_b = cls._relative_luminance(rgb_b)
        lighter = max(lum_a, lum_b)
        darker = min(lum_a, lum_b)
        return (lighter + 0.05) / (darker + 0.05)

    @classmethod
    def _best_text_color_for_bg(cls, bg_rgb):
        white = (255, 255, 255)
        black = (17, 24, 39)
        if cls._contrast_ratio(white, bg_rgb) >= cls._contrast_ratio(black, bg_rgb):
            return '#FFFFFF'
        return '#111827'

    @classmethod
    def _extract_bg_rgb(cls, style_map):
        color = cls._extract_color_from_css_value(style_map.get('background-color', ''))
        if color:
            return color
        return cls._extract_color_from_css_value(style_map.get('background', ''))

    @staticmethod
    def _has_background_image(style_map):
        bg_image = style_map.get('background-image', '').lower()
        bg = style_map.get('background', '').lower()
        return 'url(' in bg_image or 'url(' in bg

    @staticmethod
    def _ensure_background_overlay(style_map):
        overlay = 'linear-gradient(rgba(0, 0, 0, 0.58), rgba(0, 0, 0, 0.58))'
        bg_image = style_map.get('background-image', '')
        bg = style_map.get('background', '')

        if bg_image and 'url(' in bg_image and 'linear-gradient' not in bg_image.lower():
            style_map['background-image'] = f'{overlay}, {bg_image}'
            return

        if bg and 'url(' in bg and 'linear-gradient' not in bg.lower():
            style_map['background'] = f'{overlay}, {bg}'

    def _enforce_text_visibility_guardrails(self, html):
        source = (html or '').strip()
        if not source:
            return source

        try:
            wrapper = lxml_html.fromstring(f'<div>{source}</div>')
        except Exception:
            return source

        candidate_blocks = wrapper.xpath(
            './/section | .//div | .//td | .//th'
        )

        for block in candidate_blocks:
            style_map = self._parse_style_map(block.get('style', ''))
            has_bg_image = self._has_background_image(style_map)
            if has_bg_image:
                self._ensure_background_overlay(style_map)

            bg_rgb = self._extract_bg_rgb(style_map)
            if has_bg_image and not bg_rgb:
                bg_rgb = (20, 24, 32)

            if not bg_rgb:
                if style_map:
                    block.set('style', self._style_map_to_string(style_map))
                continue

            target_color = self._best_text_color_for_bg(bg_rgb)
            style_map['color'] = target_color
            block.set('style', self._style_map_to_string(style_map))

            for text_node in block.xpath(
                './/h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6 | .//p | .//span | .//a | .//li | .//strong | .//em | .//small | .//label'
            ):
                text_style_map = self._parse_style_map(text_node.get('style', ''))
                text_style_map['color'] = target_color
                text_node.set('style', self._style_map_to_string(text_style_map))

        result = lxml_html.tostring(wrapper, encoding='unicode')
        if result.startswith('<div>') and result.endswith('</div>'):
            return result[5:-6]
        return result


    # =====================================================
    # WRAP FOR ODOO BUILDER
    # =====================================================

    @staticmethod
    def _class_list(node):
        return (node.get('class') or '').split()

    @staticmethod
    def _is_element(node):
        return isinstance(getattr(node, 'tag', None), str)

    def _snippet_name_from_node(self, node):
        snippet_name = (node.get('data-snippet') or '').strip()
        if snippet_name:
            return snippet_name
        for cls in self._class_list(node):
            if cls.startswith('s_'):
                return cls
        return ''

    def _is_snippet_block_node(self, node):
        if not self._is_element(node):
            return False
        if node.tag not in ('section', 'div'):
            return False
        return bool(self._snippet_name_from_node(node))

    @staticmethod
    def _snippet_label(snippet):
        labels = {
            's_cover': 'Cover',
            's_title': 'Title',
            's_text_block': 'Text',
            's_image_text': 'Image - Text',
            's_text_image': 'Text - Image',
            's_call_to_action': 'Call to Action',
            's_footer_social': 'Footer',
            's_mail_block_footer_social': 'Footer',
            's_mail_block_footer_social_left': 'Footer',
            's_mail_block_header_social': 'Header',
            's_mail_block_header_logo': 'Header Logo',
            's_hr': 'Separator',
            's_picture': 'Picture',
            's_text_highlight': 'Text Highlight',
        }
        return labels.get(snippet, 'Text')

    @staticmethod
    def _iter_descendants(node):
        yield from node.iterdescendants()

    def _normalize_snippet_key(self, snippet_key):
        snippet_key = (snippet_key or '').strip()
        snippet_key = SNIPPET_ALIASES.get(snippet_key, snippet_key)
        if snippet_key in SNIPPET_VERSION_ATTRS:
            return snippet_key
        return DEFAULT_EDITOR_SNIPPET

    def _clean_nested_snippet_metadata(self, node):
        for descendant in self._iter_descendants(node):
            for attr in ('data-snippet', 'data-name', 'data-vxml', 'data-vcss', 'data-vjs'):
                descendant.attrib.pop(attr, None)

    def _apply_snippet_metadata(self, node, snippet_key):
        snippet_key = self._normalize_snippet_key(snippet_key)
        classes = self._class_list(node)
        if snippet_key not in classes:
            classes.append(snippet_key)
        if 'o_mail_snippet_general' not in classes:
            classes.append('o_mail_snippet_general')
        node.set('class', ' '.join(dict.fromkeys(classes)))
        node.set('data-snippet', snippet_key)
        node.set('data-name', self._snippet_label(snippet_key))
        node.attrib.pop('data-vxml', None)
        node.attrib.pop('data-vcss', None)
        node.attrib.pop('data-vjs', None)
        for attr_name, attr_value in SNIPPET_VERSION_ATTRS.get(snippet_key, {}).items():
            node.set(attr_name, attr_value)
        return node

    def _new_text_section(self, text=' '):
        section = lxml_html.Element('section')
        section.set('class', 's_text_block o_mail_snippet_general pt16 pb16')
        self._apply_snippet_metadata(section, DEFAULT_EDITOR_SNIPPET)
        paragraph = lxml_html.Element('p')
        paragraph.text = text
        section.append(paragraph)
        return section

    def _to_snippet_section(self, node):
        if not self._is_element(node):
            return None

        node = deepcopy(node)
        self._clean_nested_snippet_metadata(node)
        classes = self._class_list(node)
        snippet_class = self._snippet_name_from_node(node)

        if self._is_snippet_block_node(node):
            if snippet_class and snippet_class not in classes:
                classes = [*classes, snippet_class]
                node.set('class', ' '.join(dict.fromkeys(classes)))
            return self._apply_snippet_metadata(node, node.get('data-snippet') or snippet_class)

        if not snippet_class:
            snippet_class = DEFAULT_EDITOR_SNIPPET
            classes = [snippet_class, 'o_mail_snippet_general', 'pt16', 'pb16', *classes]

        section = lxml_html.Element('section')
        section.set('class', ' '.join(dict.fromkeys(classes)))
        self._apply_snippet_metadata(section, snippet_class)
        section.append(node)
        return section

    def _collect_top_level_snippet_blocks(self, content_root):
        direct_blocks = [
            child
            for child in list(content_root)
            if self._is_snippet_block_node(child)
        ]
        if direct_blocks:
            return [self._to_snippet_section(node) for node in direct_blocks]

        nested_blocks = []
        for node in content_root.iterdescendants():
            if not self._is_snippet_block_node(node):
                continue

            has_snippet_ancestor = any(
                self._is_snippet_block_node(ancestor)
                for ancestor in node.iterancestors()
            )
            if has_snippet_ancestor:
                continue

            nested_blocks.append(self._to_snippet_section(node))

        return nested_blocks

    def _normalize_editor_sections(self, source):
        wrapper = lxml_html.fragment_fromstring(
            f'<div>{source}</div>',
            create_parent=False,
        )

        for bad_tag in wrapper.xpath('.//script|.//style|.//meta|.//link|.//title'):
            bad_tag.drop_tree()

        # Reuse existing mailing structure when present.
        structure_nodes = wrapper.xpath(
            './/*[contains(concat(" ", normalize-space(@class), " "), " oe_structure ")]'
        )
        content_root = structure_nodes[0] if structure_nodes else wrapper

        # Remove inline event handlers to prevent JS interference
        for elem in wrapper.xpath('.//*'):
            for attr in list(elem.attrib):
                if attr.lower().startswith('on'):
                    del elem.attrib[attr]

        sections = self._collect_top_level_snippet_blocks(content_root)

        if not sections:
            for child in list(content_root):
                block = self._to_snippet_section(child)
                if block is not None:
                    sections.append(block)

        if not sections and (content_root.text or '').strip():
            sections.append(
                self._new_text_section(content_root.text.strip())
            )

        if not sections:
            sections.append(
                self._new_text_section(' ')
            )

        return '\n'.join(
            lxml_html.tostring(section, encoding='unicode')
            for section in sections
        )

    @staticmethod
    def _is_wrapped_mailing_layout(html):
        source = (html or '')
        return (
            'o_layout' in source
            and 'o_mail_wrapper' in source
            and 'o_mail_wrapper_td' in source
            and 'oe_structure' in source
        )

    def _to_mailing_layout_arch(self, html):

        source = (html or '').strip()

        if not source:
            return source

        if self._is_wrapped_mailing_layout(source):
            return source

        try:
            normalized_sections = self._normalize_editor_sections(source)
        except Exception:
            # Keep generation resilient even if the model returns broken HTML.
            normalized_sections = f"""
<section class="s_text_block o_mail_snippet_general pt16 pb16"
         data-snippet="s_text_block"
         data-vxml="001"
         data-name="Text">
    {source}
</section>
""".strip()

        return f"""
<div data-name="Mailing"
     class="o_layout oe_unremovable oe_unmovable o_default_theme"
     style="background-color:#F7F7F7;">
    <div class="container o_mail_wrapper o_mail_regular oe_unremovable">
        <div class="row mw-100 mx-0">
            <div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable"
                 style="text-align:left;width:100%;">
                {normalized_sections}
            </div>
        </div>
    </div>
</div>
""".strip()


    # =====================================================
    # GENERATE TEMPLATE
    # =====================================================

    def action_generate(self):

        self.ensure_one()

        prompt = self._build_prompt()

        data = self._call_openrouter(prompt)

        subject, html = self._parse_response(
            data
        )

        # =============================================
        # Inject curated real images
        # =============================================

        html = self._inject_real_images(
            html
        )

        html = self._materialize_external_images(
            html
        )

        html = self._enforce_text_visibility_guardrails(
            html
        )

        preview_html = self._disable_preview_click_targets(
            html
        )

        # =============================================
        # Wrap for Odoo editor
        # =============================================

        raw_mailing_html = (
            self._to_mailing_layout_arch(
                html
            )
        )

        mailing_html = (
            self._to_mailing_layout_arch(
                preview_html
            )
        )

        # Prevent click events on images inside the read-only HTML widget (rendered inside a sandboxed iframe)
        # to avoid Odoo editor's Owl lifecycle crash.
        preview_style = (
            '<style id="preview-pointer-events-override">'
            'img { pointer-events: none !important; user-select: none !important; -webkit-user-drag: none !important; cursor: default !important; }'
            '</style>'
        )
        mailing_html = preview_style + mailing_html

        usage = data.get(
            'usage',
            {}
        )

        self.write({
            'generated_subject': subject,
            'generated_body': mailing_html,
            'generated_body_raw': raw_mailing_html,
            'is_generated': True,
            'tokens_used': usage.get(
                'total_tokens',
                0
            ),
            'model_used': data.get(
                'model',
                self.model_id
            ),
            'error_message': False,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


    # =====================================================
    # REGENERATE
    # =====================================================

    def action_regenerate(self):

        self.write({
            'is_generated': False,
            'generated_subject': False,
            'generated_body': False,
            'generated_body_raw': False,
        })

        return self.action_generate()


    # =====================================================
    # CREATE TEMPLATE
    # =====================================================

    def action_create_template(self):

        self.ensure_one()

        if not self.generated_body:

            raise UserError(_(
                'Please generate template first.'
            ))

        source_mailing = self.env[
            'mailing.mailing'
        ]

        if (
            self.source_model == 'mailing.mailing'
            and self.source_id
        ):

            source_mailing = (
                self.env[
                    'mailing.mailing'
                ]
                .browse(self.source_id)
                .exists()
            )

        if not source_mailing:

            active_id = self.env.context.get(
                'active_id'
            )

            if active_id:

                source_mailing = (
                    self.env[
                        'mailing.mailing'
                    ]
                    .browse(active_id)
                    .exists()
                )

        mailing_model_id = (
            source_mailing.mailing_model_id.id
            if source_mailing
            else self.env.ref(
                'mass_mailing.model_mailing_list'
            ).id
        )

        template_name = (
            self.generated_subject
            or 'AI Generated Template'
        )

        source_html = self.generated_body_raw or self.generated_body

        html = (
            source_html
            if self._is_wrapped_mailing_layout(source_html)
            else self._to_mailing_layout_arch(source_html)
        )

        html = self._materialize_external_images(html)

        html = self._enforce_text_visibility_guardrails(html)

        if html and '<style id="preview-pointer-events-override">' in html:
            html = re.sub(
                r'<style id="preview-pointer-events-override">.*?</style>',
                '',
                html,
                flags=re.DOTALL
            ).strip()

        vals = {
            'name': f'AI Template: {template_name}',
            'subject': template_name,
            'mailing_type': 'mail',
            'mailing_model_id': mailing_model_id,
            'favorite': True,
            'user_id': self.env.user.id,
            'body_arch': html,
            'body_html': html,
        }

        self.env[
            'mailing.mailing'
        ].create(vals)

        # =============================================
        # APPLY TO CURRENT MAILING
        # =============================================

        if source_mailing:

            update_vals = {
                'body_arch': html,
                'body_html': html,
            }

            if (
                self.include_subject
                and self.generated_subject
            ):

                update_vals['subject'] = (
                    self.generated_subject
                )

            source_mailing.write(
                update_vals
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
