from odoo import models, _


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    # def action_open_ai_wizard(self):
    #     """Open the AI template generator wizard from Email Marketing."""
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('✨ AI Email Generator'),
    #         'res_model': 'ai.template.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_source_model': 'mailing.mailing',
    #             'default_source_id': self.id,
    #             'dialog_size': 'medium',
    #         },
    #     }

    def action_open_ai_styled_wizard(self):
        """Open the AI styled template generator wizard from Email Marketing."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('🎨 AI Template by Style'),
            'res_model': 'ai.styled.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_model': 'mailing.mailing',
                'default_source_id': self.id,
                'dialog_size': 'large',
            },
        }

    def action_open_ai_subject_wizard(self):
        """Open the AI subject line generator wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('✨ AI Subject Line Generator'),
            'res_model': 'ai.subject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mailing_id': self.id,
                'default_current_subject': self.subject or '',
                'dialog_size': 'medium',
            },
        }
