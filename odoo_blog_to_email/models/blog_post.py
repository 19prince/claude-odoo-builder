import html
import logging
import re

from odoo import models

_logger = logging.getLogger(__name__)

SLOT_START = '<!-- BLOG_POSTS_SLOT:START -->'
SLOT_END   = '<!-- BLOG_POSTS_SLOT:END -->'

MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"
SANS = "'Inter Tight', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"

LABELS = [
    '01 &nbsp;&middot;&nbsp; LATEST',
    '02 &nbsp;&middot;&nbsp; PREVIOUS',
    '03 &nbsp;&middot;&nbsp; EARLIER',
    '04 &nbsp;&middot;&nbsp; RECENT',
    '05 &nbsp;&middot;&nbsp; RECENT',
]


def _clean_teaser(raw, title):
    text = re.sub(r'[​‌‍﻿]+', ' ', raw or '')
    text = re.sub(r'\s+', ' ', text).strip()
    if text.startswith(title):
        text = text[len(title):].strip()
    text = re.sub(r'^[A-Z][a-z]+ \d{1,2},?\s+\d{4}\s*', '', text).strip()
    text = re.sub(r'^TL;DR\s*', '', text, flags=re.IGNORECASE).strip()
    if len(text) > 160:
        text = text[:160].rsplit(' ', 1)[0] + '...'
    return text or 'Read the full post on the blog.'


def _render_slot(index, title, teaser, url, is_last, labels, base_url):
    label = labels[index] if index < len(labels) else f'{index + 1:02d} &nbsp;&middot;&nbsp; RECENT'
    safe_url = html.escape(base_url.rstrip('/') + url)

    if is_last:
        cell_style = 'padding-top: 24px;'
    elif index == 0:
        cell_style = 'padding-bottom: 24px; border-bottom: 1px solid #e9edf3;'
    else:
        cell_style = 'padding: 24px 0; border-bottom: 1px solid #e9edf3;'

    safe_title  = html.escape(title)
    safe_teaser = html.escape(teaser)

    return (
        f'        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse;">\n'
        f'            <tr>\n'
        f'                <td style="{cell_style}">\n'
        f'                    <p style="font-family: {MONO}; font-size: 10px; font-weight: 500; letter-spacing: .12em; text-transform: uppercase; color: #a9b3c2; margin: 0 0 8px 0;">{label}</p>\n'
        f'                    <p style="font-family: {SANS}; font-weight: 700; font-size: 18px; line-height: 1.2; letter-spacing: -0.02em; color: #071222; margin: 0 0 8px 0;">{safe_title}</p>\n'
        f'                    <p style="font-family: {SANS}; font-weight: 400; font-size: 14px; line-height: 1.55; color: #525c6d; margin: 0 0 12px 0;">{safe_teaser}</p>\n'
        f'                    <a href="{safe_url}" style="font-family: {SANS}; font-size: 13px; font-weight: 600; color: #EA6C08; text-decoration: none; letter-spacing: -0.01em;">Read &#8594;</a>\n'
        f'                </td>\n'
        f'            </tr>\n'
        f'        </table>\n'
    )


def _build_posts_block(posts, base_url):
    slots = []
    for i, post in enumerate(posts):
        title  = post.get('name') or ''
        teaser = _clean_teaser(post.get('teaser') or '', title)
        url    = post.get('website_url') or '/'
        slots.append(_render_slot(i, title, teaser, url, is_last=(i == len(posts) - 1), labels=LABELS, base_url=base_url))

    inner = '\n'.join(slots)
    return (
        f'<div class="s_text_block o_mail_snippet_general" style="background-color: #ffffff; padding: 0 32px 40px;" data-snippet="s_text_block" data-name="RecentPosts">\n'
        f'    <div class="container s_allow_columns">\n\n'
        f'        <hr style="border: 0; border-top: 1px solid #d3dae4; margin: 0 0 32px 0;">\n\n'
        f'        <p style="font-family: {MONO}; font-size: 11px; font-weight: 500; letter-spacing: .16em; text-transform: uppercase; color: #5DA9FF; margin: 0 0 28px 0;">RECENT POSTS</p>\n\n'
        f'{inner}'
        f'    </div>\n'
        f'</div>'
    )


class BlogPost(models.Model):
    _inherit = 'blog.post'

    def write(self, vals):
        # Snapshot published state before the write
        old_published = {rec.id: rec.is_published for rec in self}
        result = super().write(vals)

        # Only proceed if published state or tags changed, and we're not in a recursive call
        if self.env.context.get('_obte_auto_refresh'):
            return result

        if 'is_published' not in vals and 'tag_ids' not in vals:
            return result

        get_param = self.env['ir.config_parameter'].sudo().get_param
        tag_name = (get_param('odoo_blog_to_email.auto_mailing_tag') or 'Newsletter').lower()

        for rec in self:
            just_published = (
                vals.get('is_published') is True
                and not old_published.get(rec.id)
            )
            has_matching_tag = any(
                t.name.lower() == tag_name for t in rec.tag_ids
            )
            if just_published and has_matching_tag:
                self.with_context(_obte_auto_refresh=True)._refresh_auto_mailing()
                break  # one refresh per write call is enough

        return result

    def _refresh_auto_mailing(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param

        mailing_id_str = get_param('odoo_blog_to_email.auto_mailing_id')
        if not mailing_id_str:
            _logger.warning('odoo_blog_to_email: auto_mailing_id not configured — skipping refresh')
            return

        try:
            mailing_id = int(mailing_id_str)
        except (TypeError, ValueError):
            _logger.warning('odoo_blog_to_email: invalid auto_mailing_id %r — skipping', mailing_id_str)
            return

        post_count = int(get_param('odoo_blog_to_email.auto_mailing_post_count') or 3)
        tag_name   = (get_param('odoo_blog_to_email.auto_mailing_tag') or 'Newsletter').lower()
        base_url   = (get_param('web.base.url') or '').rstrip('/')

        posts = self.env['blog.post'].sudo().search_read(
            [('is_published', '=', True), ('tag_ids.name', '=ilike', tag_name)],
            ['name', 'teaser', 'post_date', 'website_url'],
            order='post_date desc',
            limit=post_count,
        )

        if not posts:
            _logger.warning('odoo_blog_to_email: no published posts with tag %r found', tag_name)
            return

        mailing = self.env['mailing.mailing'].sudo().browse(mailing_id)
        if not mailing.exists():
            _logger.warning('odoo_blog_to_email: mailing ID %s not found', mailing_id)
            return

        body = mailing.body_arch or ''
        if SLOT_START not in body or SLOT_END not in body:
            _logger.warning(
                'odoo_blog_to_email: slot markers not found in mailing %s body — skipping',
                mailing_id,
            )
            return

        posts_block = _build_posts_block(posts, base_url)
        new_body = re.sub(
            r'<!-- BLOG_POSTS_SLOT:START -->.*?<!-- BLOG_POSTS_SLOT:END -->',
            f'{SLOT_START}\n{posts_block}\n{SLOT_END}',
            body,
            flags=re.DOTALL,
        )

        mailing.sudo().write({'body_arch': new_body, 'body_html': new_body})
        _logger.info(
            'odoo_blog_to_email: refreshed mailing %s with %s post(s)',
            mailing_id, len(posts),
        )
