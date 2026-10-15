from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Flag ลงนามในใบปะหน้า as the number-issuing verb (ADR-0017).

    The built-in verbs are ``noupdate`` data, so the new ``issues_number`` value
    in sarabun_verb_data.xml never reaches an existing database on upgrade.

    A draft/returned หนังสือ whose Route was seeded before this change (e.g. from the
    old อนุมัติ-only templates) has no issuing step and could no longer be sent, so
    its waiting อนุมัติ steps become ลงนามในใบปะหน้า — the same swap made in those
    templates. Both verbs carry identical gating/signature flags.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    verb = env.ref("agx_sarabun.verb_sign_approve", raise_if_not_found=False)
    if not verb:
        return
    verb.issues_number = True
    approve = env.ref("agx_sarabun.verb_approve", raise_if_not_found=False)
    if not approve:
        return
    env["sarabun.verb"].flush_model()
    cr.execute(
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
