import logging

from odoo import SUPERUSER_ID, api
from odoo.exceptions import UserError

from odoo.addons.agx_sarabun.models.sarabun_routing_step import POSITIVE_DISPOSITIONS

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Flag ลงนามในใบปะหน้า as the number-issuing verb (ADR-0017).

    The built-in verbs are ``noupdate`` data, so the new ``issues_number`` value
    in sarabun_verb_data.xml never reaches an existing database on upgrade.

    A draft/returned หนังสือ whose Route was seeded before this change (e.g. from the
    old อนุมัติ-only templates) has no issuing step and could no longer be sent, so
    its waiting อนุมัติ steps become ลงนามในใบปะหน้า — the same swap made in those
    templates. Both verbs carry identical gating/signature flags.

    A circulating หนังสือ already past its ใบปะหน้า sign stayed unnumbered under
    ADR-0010; under ADR-0017 it should carry its number now, so those are numbered
    in the order they were signed. Returned/draft ones are numbered at their next
    issuing sign.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    verb = env.ref("agx_sarabun.verb_sign_approve", raise_if_not_found=False)
    if not verb:
        return
    verb.issues_number = True
    _swap_unsendable_approve_steps(env, verb)
    _backfill_signed_numbers(env)


def _swap_unsendable_approve_steps(env, verb):
    approve = env.ref("agx_sarabun.verb_approve", raise_if_not_found=False)
    if not approve:
        return
    env["sarabun.verb"].flush_model()
    env.cr.execute(
        """
        UPDATE sarabun_routing_step s
           SET verb = %(sign)s
          FROM sarabun_document d
         WHERE s.document_id = d.id
           AND d.state IN ('draft', 'returned')
           AND s.active
           AND s.state = 'waiting'
           AND s.verb = %(approve)s
           AND NOT EXISTS (
                SELECT 1
                  FROM sarabun_routing_step s2
                  JOIN sarabun_verb v ON v.id = s2.verb
                 WHERE s2.document_id = d.id
                   AND s2.active
                   AND v.issues_number
           )
        """,
        {"sign": verb.id, "approve": approve.id},
    )
    env["sarabun.routing.step"].invalidate_model(["verb"])


def _backfill_signed_numbers(env):
    def _issued_at(doc):
        signs = doc.routing_step_ids.filtered(
            lambda s: s.state == "done"
            and s.disposition in POSITIVE_DISPOSITIONS
            and s.verb.issues_number
        )
        return min(signs.mapped("acted_date")) if signs else False

    docs = env["sarabun.document"].search(
        [("state", "=", "circulating"), ("register_number_id", "=", False)]
    )
    pending = [(doc, _issued_at(doc)) for doc in docs]
    for doc, _signed in sorted(
        (p for p in pending if p[1]), key=lambda p: (p[1], p[0].id)
    ):
        try:
            with env.cr.savepoint():
                doc._assign_register_number()
        except UserError as e:
            # e.g. its เล่มทะเบียน was archived since — don't abort the upgrade;
            # it is still numbered at completion (safety net) once fixed.
            _logger.warning("Could not backfill a number for %s: %s", doc, e)
            continue
        doc.message_post(
            body="ออกเลขที่หนังสือย้อนหลัง (ลงนามในใบปะหน้าแล้วก่อนอัปเกรด — ADR-0017)"
        )
        _logger.info("Backfilled register number %s on %s", doc.name, doc)
