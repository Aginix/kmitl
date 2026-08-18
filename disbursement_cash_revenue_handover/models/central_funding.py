# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class KmitlCentralFunding(models.Model):
    """Where a source of funds is held centrally, and under which dimensions.

    One row per (source of funds x company). The row's very existence is the
    rule that says "money from this source is held centrally, so spending it
    anywhere else has to be funded by a handover" — no source of funds is named
    in code, which is what lets a new source be brought into scope from the
    configuration screen alone.
    """

    _name = "kmitl.central.funding"
    _description = "Central Funding Profile"
    _order = "source_analytic_id"

    source_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Source of Funds",
        required=True,
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "sources")],
        help="The source of funds this profile describes. Only disbursements "
        "carrying this source are handed over, and a handover never crosses "
        "from one source to another.",
    )
    bank_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cash/Bank Account",
        required=True,
        check_company=True,
        domain="[('account_type', '=', 'asset_cash'),"
        " ('deprecated', '=', False),"
        " ('company_id', 'in', allowed_company_ids)]",
        help="GL account the money physically sits in. A handover credits it at "
        "central's dimensions and debits it at the spending unit's — the same "
        "account on both sides, because the cash itself does not move.",
    )
    revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Revenue Account",
        required=True,
        check_company=True,
        domain="[('account_type', 'in', ('income', 'income_other')),"
        " ('deprecated', '=', False),"
        " ('company_id', 'in', allowed_company_ids)]",
        help="GL account the money was recognised as revenue under when it "
        "arrived. A handover reverses that recognition at central and makes it "
        "again at the spending unit.",
    )
    central_department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Central Department",
        required=True,
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "departments")],
        help="The department holding the money. A disbursement whose own "
        "department is this one — or sits under it — is already spending where "
        "the money is held, so it gets no handover.",
    )
    central_fund_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Central Fund",
        required=True,
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "funds")],
        help="The fund the money is held under centrally. The spending unit's "
        "side of a handover uses the fund on the disbursement instead, which is "
        "usually a different one.",
    )
    central_activity_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Central Activity",
        required=True,
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "activities")],
        help="The activity the money is recognised under when it arrives "
        "centrally. It is a fixed value, not derived from the disbursement: "
        "central parks every receipt of this source on the one activity, while "
        "the spending unit's side of a handover uses the activity on the "
        "disbursement.",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        check_company=True,
        domain="[('type', '=', 'general'),"
        " ('company_id', 'in', allowed_company_ids)]",
        default=lambda self: self._default_journal_id(),
        help="Journal the handover entry is booked in.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "source_company_unique",
            "unique(source_analytic_id, company_id)",
            "A central funding profile already exists for this source of funds.",
        ),
    ]

    @api.model
    def _default_journal_id(self):
        """ใบสำคัญทั่วไป (JV) — the general journal ``account_kmitl`` seeds.

        Looked up rather than ``ref``'d hard: the journal is created by that
        module's post-init hook, so on a database whose chart was never set up
        there is none, and a missing default must not stop the form opening.
        """
        journal = self.env.ref("account_kmitl.journal_jv", raise_if_not_found=False)
        if journal and journal.company_id == self.env.company:
            return journal.id
        return False

    def name_get(self):
        return [(record.id, record.source_analytic_id.display_name) for record in self]

    @api.model
    def _for_request(self, request):
        """The profile governing a disbursement request, empty if there is none.

        An empty result is the answer "this disbursement is not spending
        centrally-held money", which is why the caller treats it as a plain skip
        rather than an error.
        """
        source = request.source_analytic_id
        if not source:
            return self.browse()
        return self.search(
            [
                ("source_analytic_id", "=", source.id),
                ("company_id", "=", request.company_id.id),
            ],
            limit=1,
        )

    def covers_department(self, department):
        """Whether ``department`` is central itself or sits underneath it."""
        self.ensure_one()
        central = self.central_department_analytic_id
        if not department or not central:
            return False
        ancestors = self.env["budget.controller"]._self_and_ancestor_ids(department)
        return central.id in ancestors
