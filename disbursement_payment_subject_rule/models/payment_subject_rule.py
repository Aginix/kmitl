# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementPaymentSubjectRule(models.Model):
    """Rule that picks the payment subject (เรื่องที่จ่าย) of a disbursement request.

    A billed request without a subject is matched against these rules (ordered by
    ``sequence``) and the first matching rule's subject is set on it. Matching is
    advisory: it only pre-fills the subject, which the auditor may still change
    while it is theirs to choose.
    """

    _name = "disbursement.payment.subject.rule"
    _description = "Disbursement Payment Subject Rule"
    _order = "sequence, id"
    _rec_name = "payment_subject_id"

    # Hierarchical dimension criteria, matched over the whole ancestor subtree.
    # An empty criterion behaves as a wildcard (matches any value there).
    _CRITERIA = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # -- criteria: empty = wildcard --------------------------------------
    # ``ondelete="restrict"`` prevents a rule from silently turning into a
    # wildcard when the referenced record is removed.
    partner_type_id = fields.Many2one(
        "res.partner.type",
        string="Payee Type",
        ondelete="restrict",
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "sources")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "activities")],
    )
    # Same keys as ``disbursement.request.payment_type``.
    payment_type = fields.Selection(
        selection=[
            ("direct", "Direct paid"),
            ("advance", "Advance"),
            ("prepaid", "Prepaid"),
        ],
        string="Payment Type",
    )

    payment_subject_id = fields.Many2one(
        "kmitl.payment.subject",
        string="Payment Subject",
        required=True,
        ondelete="restrict",
    )

    @api.model
    def _find_for_request(self, request):
        """Return the first rule (by sequence) matching ``request``.

        Hierarchical dimensions match on the whole ancestor subtree, as
        ``finance.assignment.rule`` does: a rule set on a parent account covers
        requests on any of its descendants. Payee type and payment type are
        flat, so both match on equality.
        """
        domain = [("active", "=", True)]
        for field in self._CRITERIA:
            ancestors = [
                int(i)
                for i in (request[field].parent_path or "").strip("/").split("/")
                if i
            ]
            domain.append((field, "in", ancestors + [False]))
        domain.append(
            ("partner_type_id", "in", request.partner_type_id.ids + [False])
        )
        domain.append(("payment_type", "in", [request.payment_type, False]))
        return self.search(domain, limit=1)
