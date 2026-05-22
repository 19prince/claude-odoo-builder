{
    'name': 'Odoo Blog to Email',
    'version': '18.0.1.0.0',
    'category': 'Email Marketing',
    'summary': 'Refreshes a mailing when a tagged blog post is published. Configurable in Settings.',
    'author': '19 Prince',
    'website': 'https://www.19prince.com',
    'license': 'LGPL-3',
    'depends': ['blog', 'mass_mailing', 'general_settings'],
    'data': ['views/res_config_settings_views.xml'],
    'installable': True,
    'auto_install': False,
}
