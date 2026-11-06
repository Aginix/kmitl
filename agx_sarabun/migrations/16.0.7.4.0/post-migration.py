from odoo import SUPERUSER_ID, api

BUTTON_EMOJI = {
    "verb_originate": "✍️",
    "verb_prepare": "📝",
    "verb_acknowledge": "👀",
    "verb_acknowledge_sign": "✍️",
    "verb_verify": "🔍",
    "verb_consider": "🗂️",
    "verb_forward": "🖊️",
    "verb_endorse": "💬",
    "verb_sign_approve": "✍️",
    "verb_approve": "👍",
}


def migrate(cr, version):
    """Keep today's behaviour: every signing verb keeps its comment box (now
    ความเห็นในการลงนาม); seed the act-button emoji of the built-in verbs (data is
    noupdate)."""
    cr.execute("UPDATE sarabun_verb SET allow_sign_comment = show_signature")
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, emoji in BUTTON_EMOJI.items():
        verb = env.ref("agx_sarabun." + xmlid, raise_if_not_found=False)
        if verb and not verb.button_emoji:
            verb.button_emoji = emoji
