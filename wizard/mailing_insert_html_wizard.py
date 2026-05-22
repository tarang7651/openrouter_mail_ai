from odoo import models, fields, _
import logging
import base64
import mimetypes
import html as py_html
import re
from urllib.parse import urlparse

from lxml import html as lxml_html
import requests

_logger = logging.getLogger(__name__)


class MailingInsertHtmlWizard(models.TransientModel):
    _name = 'mailing.insert.html.wizard'
    _description = 'Insert HTML into Mailing'

    html_content = fields.Text(string='HTML Content', required=True)

    @staticmethod
    def _node_inner_html(node):
        parts = []
        if node.text:
            parts.append(node.text)
        for child in node:
            parts.append(lxml_html.tostring(child, encoding='unicode'))
        return ''.join(parts)

    def _normalize_pasted_html(self, html):
        source = (html or '').strip()
        if not source:
            return source

        # Backward compatibility for older rich-text input that stored escaped HTML.
        if '&lt;' in source and '&gt;' in source:
            source = re.sub(r'<br\s*/?>', '\n', source, flags=re.IGNORECASE)
            source = re.sub(r'</p>\s*<p[^>]*>', '\n', source, flags=re.IGNORECASE)
            source = re.sub(r'</?p[^>]*>', '', source, flags=re.IGNORECASE).strip()
            decoded = py_html.unescape(source)
            if re.search(r'<[a-zA-Z!/][^>]*>', decoded or ''):
                source = decoded.strip()

        # If user pastes a full HTML document, only keep body content.
        if any(tag in source.lower() for tag in ('<!doctype', '<html', '<head', '<body')):
            try:
                document = lxml_html.document_fromstring(source)
                body_nodes = document.xpath('//body')
                if body_nodes:
                    body_html = self._node_inner_html(body_nodes[0]).strip()
                    if body_html:
                        source = body_html
            except Exception:
                match = re.search(r'<body[^>]*>(.*?)</body>', source, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    source = match.group(1).strip()

        return source

    def _is_external_image_src(self, src):
        source = (src or '').strip().lower()
        if not source:
            return False
        return source.startswith(('http://', 'https://'))

    def _guess_mimetype(self, url, response):
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
            filename = f'inserted_image{extension}'

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

    def _to_mailing_layout_arch(self, html):
        source = (html or '').strip()
        if not source:
            return '<section class="s_text_block o_mail_snippet_general pt16 pb16" data-snippet="s_text_block" data-vxml="001" data-name="Text"><p> </p></section>'

        if 'o_layout' in source and 'oe_structure' in source:
            return source

        try:
            wrapper = lxml_html.fromstring(f'<div>{source}</div>')
        except Exception:
            return f"""<div data-name="Mailing" class="o_layout oe_unremovable oe_unmovable o_default_theme" style="background-color:#F7F7F7;">
    <div class="container o_mail_wrapper o_mail_regular oe_unremovable">
        <div class="row mw-100 mx-0">
            <div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable" style="text-align:left;width:100%;">
                {source}
            </div>
        </div>
    </div>
</div>"""

        snippet_classes = ['s_text_block', 's_title', 's_cover', 's_text_image', 's_image_text', 
                          's_call_to_action', 's_picture', 's_hr', 's_text_highlight',
                          's_mail_block_footer_social', 's_mail_block_header_social']
        
        snippet_nodes = []
        for node in wrapper.iter():
            node_classes = (node.get('class') or '').split()
            is_snippet = any(cls in snippet_classes for cls in node_classes)
            if is_snippet:
                snippet_nodes.append(node)
        
        if snippet_nodes:
            output_parts = []
            for node in snippet_nodes:
                classes = (node.get('class') or '').split()
                snippet_key = None
                for cls in classes:
                    if cls in snippet_classes:
                        snippet_key = cls
                        break
                
                if snippet_key:
                    if 'o_mail_snippet_general' not in classes:
                        classes.append('o_mail_snippet_general')
                    if 'pt16' not in classes and 'pb16' not in classes:
                        classes.extend(['pt16', 'pb16'])
                    node.set('class', ' '.join(dict.fromkeys(classes)))
                    node.set('data-snippet', snippet_key)
                    node.set('data-vxml', '001')
                    node.set('data-name', self._snippet_label(snippet_key))
                
                output_parts.append(lxml_html.tostring(node, encoding='unicode'))
            
            if output_parts:
                content = '\n'.join(output_parts)
            else:
                content = source
        else:
            content = source

        return f"""<div data-name="Mailing" class="o_layout oe_unremovable oe_unmovable o_default_theme" style="background-color:#F7F7F7;">
    <div class="container o_mail_wrapper o_mail_regular oe_unremovable">
        <div class="row mw-100 mx-0">
            <div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable" style="text-align:left;width:100%;">
                {content}
            </div>
        </div>
    </div>
</div>"""

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

    def action_apply_html(self):
        self.ensure_one()
        mailing_id = self.env.context.get('active_id')

        if mailing_id:
            mailing = self.env['mailing.mailing'].browse(mailing_id)

            html_content = self._normalize_pasted_html(self.html_content or '')
            html_content = self._materialize_external_images(html_content)
            wrapped_html = self._to_mailing_layout_arch(html_content)

            mailing.write({
                'body_arch': wrapped_html,
                'body_html': wrapped_html,
            })

        return {'type': 'ir.actions.act_window_close'}
