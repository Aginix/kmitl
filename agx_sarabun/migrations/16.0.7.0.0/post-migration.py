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
    its last waiting อนุมัติ step becomes ลงนามในใบปะหน้า — the same swap made in
    those templates, also applied to admin-built templates. Both verbs carry
    identical gating/signature flags.

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
    """Make pre-ADR-0017 Routes and Route Templates sendable again.

    Only the LAST อนุมัติ of each Route / template becomes ลงนามในใบปะหน้า: under
    ADR-0010 the number ran at completion, i.e. at the final sign, so numbering at
    an earlier อนุมัติ (e.g. the คณบดี before the อธิการบดี) would leave a voided gap
    if a later approver rejects.
    """
    approve = env.ref("agx_sarabun.verb_approve", raise_if_not_found=False)
    if not approve:
        return
    env["sarabun.verb"].flush_model()
    params = {"sign": verb.id, "approve": approve.id}
    env.cr.execute(
        """
        UPDATE sarabun_routing_step
           SET verb = %(sign)s
         WHERE id IN (
                SELECT DISTINCT ON (s.document_id) s.id
                  FROM sarabun_routing_step s
                  JOIN sarabun_document d ON d.id = s.document_id
                 WHERE d.state IN ('draft', 'returned')
                   AND d.register_number_id IS NULL
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
              ORDER BY s.document_id, s."order" DESC, s.id DESC
         )
        """,
        params,
    )
    # Admin-built templates (incl. a type's default route) seed new drafts — fix
    # them the same way, or every draft seeded from them is blocked at ส่ง.
    env.cr.execute(
        """
        UPDATE sarabun_route_template_line
           SET verb = %(sign)s
         WHERE id IN (
                SELECT DISTINCT ON (l.template_id) l.id
                  FROM sarabun_route_template_line l
                 WHERE l.verb = %(approve)s
                   AND NOT EXISTS (
                        SELECT 1
                          FROM sarabun_route_template_line l2
                          JOIN sarabun_verb v ON v.id = l2.verb
                         WHERE l2.template_id = l.template_id
                           AND v.issues_number
                   )
              ORDER BY l.template_id, l."order" DESC, l.id DESC
         )
        """,
        params,
    )
    env["sarabun.routing.step"].invalidate_model(["verb"])
    env["sarabun.route.template.line"].invalidate_model(["verb"])


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
