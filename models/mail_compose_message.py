from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    # Temporarily disabled: AI compose wizard actions.
    # def action_open_ai_wizard(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Generate with AI'),
    #         'res_model': 'ai.template.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_source_model': self._name,
    #             'default_source_id': self.id,
    #         },
    #     }

    # def action_open_ai_styled_wizard(self):
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Generate Template by Style'),
    #         'res_model': 'ai.styled.template.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_source_model': self._name,
    #             'default_source_id': self.id,
    #             'dialog_size': 'large',
    #         },
    #     }

    # def action_open_ai_subject_wizard(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('✨ AI Subject Ideas'),
    #         'res_model': 'ai.subject.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_compose_id': self.id,
    #             'default_current_subject': self.subject or '',
    #             'dialog_size': 'medium',
    #         },
    #     }
