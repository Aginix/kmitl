import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

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
    noupdate). Then drop the old-round history (ADR-0023): delete every
    set-aside step of past attempts and reset the attempt counter."""
    cr.execute("UPDATE sarabun_verb SET allow_sign_comment = show_signature")
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, emoji in BUTTON_EMOJI.items():
        verb = env.ref("agx_sarabun." + xmlid, raise_if_not_found=False)
        if verb and not verb.button_emoji:
            verb.button_emoji = emoji
    _purge_history(env)
    _backfill_auto_followers(env)
    cr.execute("UPDATE sarabun_document SET attempt_seq = 1 WHERE attempt_seq != 1")


def _purge_history(env):
    """Delete the archived rounds (ADR-0023), logging each document and who lost
    read. Legacy steps carry no record of which followers the engine added, so the
    old round's holders the หนังสือ no longer reaches are unfollowed outright."""
    Step = env["sarabun.routing.step"].with_context(active_test=False)
    old = Step.search([("active", "=", False)])
    _logger.info(
        "agx_sarabun: purging %s archived steps on %s documents (ADR-0023)",
        len(old),
        len(old.document_id),
    )
    # a หนังสือ waiting in ตีกลับ keeps its banner: copy the return off the step first
    for doc in old.document_id.filtered(lambda d: d.state == "returned"):
        ret = old.filtered(
            lambda s: s.document_id == doc and s.disposition == "return"
        ).sorted(lambda s: s.acted_date or s.create_date)[-1:]
        if ret:
            doc.write(
                {
                    "returned_by_id": ret.acted_by_id.id,
                    "returned_date": ret.acted_date,
                    "returned_step_name": ret.verb.name,
                    "returned_reason": ret.note,
                }
            )
    for doc in old.document_id:
        before = doc.reached_user_ids
        doc._purge_archived_steps()
        gone = before - doc.reached_user_ids - doc.sender_user_id
        gone = gone.filtered(lambda u: u.partner_id in doc.message_partner_ids)
        if gone:
            doc.message_unsubscribe(partner_ids=gone.partner_id.ids)
        _logger.info(
            "agx_sarabun: document %s (%s) — unfollowed: %s",
            doc.id,
            doc.name,
            ", ".join(gone.mapped("login")) or "-",
        )


def _backfill_auto_followers(env):
    """Steps raised before auto_follower_partner_ids existed carry no record of
    the followers the engine added. Treat a live step's holders who follow the
    หนังสือ as engine-added, so a later ตีกลับ / ดึงกลับ still unfollows them."""
    steps = env["sarabun.routing.step"].search(
        [("state", "in", ("active", "done")), ("actor_user_ids", "!=", False)]
    )
    count = 0
    for step in steps:
        partners = step.actor_user_ids.partner_id & step.document_id.message_partner_ids
        partners -= step.document_id.sender_user_id.partner_id
        if partners:
            step.auto_follower_partner_ids = [(4, p.id) for p in partners]
            count += 1
    _logger.info("agx_sarabun: backfilled engine-added followers on %s steps", count)

