{
    'name': 'OpenRouter Mail AI Studio',
    'version': '1.0.0',
    'category': 'Marketing/Email Marketing',
    'summary': 'Generate AI-powered email templates via OpenRouter inside Mail Composer & Email Marketing',
    'description': """
        OpenRouter Mail AI Studio
        ============================
        Integrate 300+ AI models into Odoo's mail composer and email marketing module.
        Features:
        - ✨ Generate email templates with AI directly from the mail compose window
        - 📧 Generate & enhance campaigns inside Email Marketing
        - 🔀 Switch between any OpenRouter model (GPT-4o, Claude, Gemini, Llama, etc.)
        - 🎯 Choose tone: Professional, Casual, Formal, Persuasive, Empathetic
        - ⚙️  Centralized API key & default model configuration in Settings
    """,
    'author': 'Tarang Kushwaha',
    'website': 'https://github.com/yourname/openrouter_mail_ai',
    'license': 'OPL-1',
    'depends': ['mail', 'mass_mailing', 'mass_mailing_themes', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/ai_template_wizard_views.xml',
        'views/ai_styled_template_wizard_views.xml',
        'views/mail_compose_message_views.xml',
        'views/mailing_mailing_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
    'currency': "USD",
    'price': "100"
}
