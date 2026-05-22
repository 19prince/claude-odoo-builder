from . import models


def post_init_hook(env):
    """Point the auto_mailing_id setting at the starter mailing created by this module."""
    mailing = env.ref('odoo_blog_to_email.mailing_blog_to_email_starter', raise_if_not_found=False)
    if mailing:
        env['ir.config_parameter'].sudo().set_param('odoo_blog_to_email.auto_mailing_id', str(mailing.id))
