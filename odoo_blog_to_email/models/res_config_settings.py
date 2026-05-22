from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_mailing_id = fields.Many2one(
        'mailing.mailing',
        string='Welcome mailing',
        help='Mailing to refresh when a tagged blog post is published.',
        config_parameter='19prince.auto_mailing_id',
    )
    auto_mailing_tag = fields.Char(
        string='Blog tag',
        help='Exact tag name to watch (case-insensitive). Default: Newsletter.',
        default='Newsletter',
        config_parameter='19prince.auto_mailing_tag',
    )
    auto_mailing_post_count = fields.Integer(
        string='Number of posts',
        help='How many recent posts to inject into the mailing.',
        default=3,
        config_parameter='19prince.auto_mailing_post_count',
    )
