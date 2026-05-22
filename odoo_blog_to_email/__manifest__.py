{
    'name': 'Odoo Blog to Email',
    'version': '18.0.2.0.0',
    'category': 'Email Marketing',
    'summary': 'Refreshes a mailing when a tagged blog post is published. Configurable in Settings.',
    'author': '19 Prince',
    'website': 'https://www.19prince.com',
    'license': 'LGPL-3',
    'depends': ['website_blog', 'mass_mailing'],
    'data': [
        'data/mailing_starter.xml',
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
}
