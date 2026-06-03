import logging
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetController(models.AbstractModel):
    """Budget Controller - Centralized service for budget operations and availability checking.

    Calculates: Available = Appropriated - Reserved - Consumed

    Where:
    - Appropriated: from budget.move (appropriation/entry type)
    - Reserved: net reserve from active commitment lines (reserve lines - consume lines)
    - Consumed: consume lines from all commitments (including done)
    """

    _name = "budget.controller"
    _description = "Budget Controller Service"

    @api.model
    def check_budget_availability(
        self, analytic_data, amount, fiscal_year_id, company_id=None
    ):
        """Check if sufficient budget is available"""
        if not company_id:
            company_id = self.env.company.id

        available_amount = self.get_available_budget(
            analytic_data, fiscal_year_id, company_id
        )

        if amount > available_amount:
            error_msg = self._format_budget_shortage_message(
                analytic_data, available_amount, amount
            )
            raise ValidationError(error_msg)

        return True

    @api.model
    def get_available_budget(self, analytic_data, fiscal_year_id, company_id=None):
        """Get available budget = Appropriated - Reserved - Consumed"""
        if not company_id:
            company_id = self.env.company.id

        appropriated = self._calculate_appropriated_amount(
            analytic_data, fiscal_year_id, company_id
        )
        reserved = self._calculate_reserved_amount(
            analytic_data, fiscal_year_id, company_id
        )
        consumed = self._calculate_consumed_amount(
            analytic_data, fiscal_year_id, company_id
        )

        available = appropriated - reserved - consumed
        return max(0.0, available)

    @api.model
    def get_budget_breakdown(
        self, analytic_data, fiscal_year_id=None, company_id=None
    ):
        """Get detailed budget breakdown"""
        if not company_id:
            company_id = self.env.company.id

        if not fiscal_year_id:
            today = fields.Date.today()
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", today),
                    ("date_to", ">=", today),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            fiscal_year_id = fiscal_year.id if fiscal_year else False

        if not fiscal_year_id:
            return {
                "appropriated": 0.0,
                "reserved": 0.0,
                "consumed": 0.0,
                "available": 0.0,
                "details": [],
            }

        appropriated = self._calculate_appropriated_amount(
            analytic_data, fiscal_year_id, company_id
        )
        reserved = self._calculate_reserved_amount(
            analytic_data, fiscal_year_id, company_id
        )
        consumed = self._calculate_consumed_amount(
            analytic_data, fiscal_year_id, company_id
        )
        available = appropriated - reserved - consumed

        details = self._get_budget_transaction_details(
            analytic_data, fiscal_year_id, company_id
        )

        return {
            "appropriated": appropriated,
            "reserved": reserved,
            "consumed": consumed,
            "available": max(0.0, available),
            "details": details[:10],
        }

    @api.model
    def _get_budget_transaction_details(
        self, analytic_data, fiscal_year_id, company_id
    ):
        """Get recent budget transactions"""
        details = []

        # Appropriation moves
        BudgetMove = self.env["budget.move"]
        moves = BudgetMove.search(
            [
                ("state", "=", "posted"),
                ("move_type", "in", ("appropriation", "entry")),
                ("account_fiscal_year_id", "=", fiscal_year_id),
                ("company_id", "=", company_id),
            ],
            order="date desc",
            limit=50,
        )
        for move in moves:
            for line in move.line_ids:
                if self._line_matches_analytic_data(line, analytic_data):
                    details.append(
                        {
                            "id": line.id,
                            "date": move.date,
                            "type": "appropriation",
                            "reference": move.name,
                            "amount": abs(line.balance),
                        }
                    )

        # Commitment lines (reserve, obligate, consume)
        CommitmentLine = self.env["budget.commitment.line"]
        cl_lines = CommitmentLine.search(
            [
                ("state", "=", "posted"),
                ("commitment_id.state", "in", ["reserved", "partial", "done"]),
                ("account_fiscal_year_id", "=", fiscal_year_id),
                ("company_id", "=", company_id),
            ],
            order="date desc",
            limit=50,
        )
        for cl in cl_lines:
            if self._commitment_line_matches_analytic_data(cl, analytic_data):
                details.append(
                    {
                        "id": cl.id,
                        "date": cl.date,
                        "type": cl.move_type,
                        "reference": cl.commitment_id.name,
                        "amount": cl.amount,
                    }
                )

        details.sort(key=lambda x: x["date"], reverse=True)
        return details

    @api.model
    def reserve_budget(
        self,
        analytic_data,
        amount,
        fiscal_year_id,
        source_record=None,
        company_id=None,
    ):
        """Reserve budget by creating a commitment with a reserve line"""
        if not company_id:
            company_id = self.env.company.id

        self.check_budget_availability(
            analytic_data, amount, fiscal_year_id, company_id
        )

        commitment_data = self._prepare_service_commitment_data(
            analytic_data, amount, fiscal_year_id, source_record, company_id
        )

        commitment = self.env["budget.commitment"].create(commitment_data)
        commitment.action_reserve()

        _logger.info(
            "Reserved budget amount %s via service for %s",
            amount,
            source_record._name if source_record else "service",
        )

        return commitment

    @api.model
    def consume_budget(self, commitment_id, amount=None, source_record=None):
        """Consume budget by adding a consume line to the commitment"""
        commitment = self.env["budget.commitment"].browse(commitment_id)

        if not commitment.exists():
            raise UserError(_("Budget commitment not found."))

        if commitment.state not in ["reserved", "partial"]:
            raise UserError(
                _(
                    "Budget commitment must be in reserved or partial state to consume."
                )
            )

        # Get first reserve line for analytic info
        first_reserve = commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve" and l.state == "posted"
        )[:1]

        if not first_reserve:
            raise UserError(_("No active reserve lines found on commitment."))

        consume_amount = (
            amount if amount else commitment.available_to_consume
        )

        consume_line = self.env["budget.commitment.line"].create(
            {
                "commitment_id": commitment.id,
                "move_type": "consume",
                "account_id": first_reserve.account_id.id,
                "analytic_distribution": first_reserve.analytic_distribution,
                "amount": consume_amount,
                "name": _("Service consumption for %s")
                % (source_record._name if source_record else "system"),
            }
        )

        _logger.info(
            "Consumed budget amount %s from commitment %s via service",
            consume_amount,
            commitment.name,
        )

        return consume_line

    @api.model
    def get_budget_status(self, analytic_data, fiscal_year_id, company_id=None):
        """Get comprehensive budget status"""
        if not company_id:
            company_id = self.env.company.id

        appropriated = self._calculate_appropriated_amount(
            analytic_data, fiscal_year_id, company_id
        )
        reserved = self._calculate_reserved_amount(
            analytic_data, fiscal_year_id, company_id
        )
        consumed = self._calculate_consumed_amount(
            analytic_data, fiscal_year_id, company_id
        )
        available = max(0.0, appropriated - reserved - consumed)

        total_used = reserved + consumed
        utilization = (total_used / appropriated * 100) if appropriated > 0 else 0

        breakdown = self._get_budget_status_breakdown(
            analytic_data, fiscal_year_id, company_id
        )

        return {
            "appropriated_amount": appropriated,
            "reserved_amount": reserved,
            "consumed_amount": consumed,
            "available_amount": available,
            "total_used": total_used,
            "utilization_percentage": utilization,
            "is_over_budget": total_used > appropriated,
            "shortage_amount": max(0.0, total_used - appropriated),
            "breakdown": breakdown,
        }

    @api.model
    def get_budget_card(
        self, fiscal_year_id, account_id, analytic_distribution, company_id=None
    ):
        """Six dashboard-aligned figures for one (fiscal year, budget account,
        dimensions) combination, for the budget status card widget.

        Shapes ``get_budget_status`` into the card payload. ``used`` and
        ``remaining`` mirror ``budget.dashboard._make_row`` exactly:
            used      = breakdown['total_used']  (= Sum reserve = b + c + d)
            remaining = current - used           (may be negative)
        Deliberately NOT ``status['total_used']`` (clamped net reserve) nor
        ``available_amount`` (clamped at 0), so the card reconciles with the
        monitoring dashboard.

        ``fiscal_year_id`` is optional: when falsy it falls back to the fiscal
        year covering today, matching ``budget.commitment.mixin`` which reserves
        against today's fiscal year (e.g. approval requests carry no fiscal year
        field).
        """
        company_id = company_id or self.env.company.id
        currency_id = self.env.company.currency_id.id
        empty = {
            "ready": False,
            "currency_id": currency_id,
            "current": 0.0,
            "reserved": 0.0,
            "obligated": 0.0,
            "consumed": 0.0,
            "used": 0.0,
            "remaining": 0.0,
        }
        if not account_id:
            return empty

        if not fiscal_year_id:
            today = fields.Date.today()
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", today),
                    ("date_to", ">=", today),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            fiscal_year_id = fiscal_year.id if fiscal_year else False
        if not fiscal_year_id:
            return empty

        analytic_data = self._distribution_to_analytic_data(
            int(account_id), analytic_distribution
        )
        status = self.get_budget_status(
            analytic_data, int(fiscal_year_id), company_id
        )
        breakdown = status["breakdown"]
        current = status["appropriated_amount"]
        used = breakdown["total_used"]

        return {
            "ready": True,
            "currency_id": currency_id,
            "current": current,
            "reserved": breakdown["reserved_pending"],  # b
            "obligated": breakdown["obligated_pending"],  # c
            "consumed": breakdown["consumed"],  # d
            "used": used,  # e = b + c + d
            "remaining": current - used,  # f
        }

    @api.model
    def _distribution_to_analytic_data(self, account_id, analytic_distribution):
        """Flatten an ``analytic_distribution`` JSON into the flat target dict
        that ``get_budget_status`` / ``_get_analytic_key`` compare against.

        Each analytic account is bucketed by its ``root_plan_id.code`` (matching
        the convenience-field domains), so a sub-plan account still lands in the
        right dimension slot. Every dimension key is always present (defaulting
        to ``False``) so the matching helpers, which compare against ``False``
        for untagged records, behave correctly even for a partial distribution.
        """
        data = {
            "account_id": account_id,
            "activity_analytic_id": False,
            "department_analytic_id": False,
            "fund_analytic_id": False,
            "source_analytic_id": False,
        }
        plan_to_key = {
            "activities": "activity_analytic_id",
            "departments": "department_analytic_id",
            "funds": "fund_analytic_id",
            "sources": "source_analytic_id",
        }
        ids = [int(key) for key in (analytic_distribution or {}).keys()]
        for account in self.env["account.analytic.account"].browse(ids):
            key = plan_to_key.get(account.root_plan_id.code)
            if key:
                data[key] = account.id
        return data

    @api.model
    def _get_budget_status_breakdown(
        self, analytic_data, fiscal_year_id, company_id=None
    ):
        """Get b/c/d breakdown from commitment lines.

        Returns:
            reserved_pending (b): total_reserved - total_obligated
            obligated_pending (c): total_obligated - total_consumed
            consumed (d): total_consumed
            total_used (e): b + c + d = total_reserved
        """
        if not company_id:
            company_id = self.env.company.id

        lines = self.env["budget.commitment.line"].search(
            [
                ("state", "=", "posted"),
                ("commitment_id.state", "in", ["reserved", "partial", "done"]),
                ("account_fiscal_year_id", "=", fiscal_year_id),
                ("company_id", "=", company_id),
            ]
        )

        total_reserved = 0.0
        total_obligated = 0.0
        total_consumed = 0.0

        for line in lines:
            if self._commitment_line_matches_analytic_data(line, analytic_data):
                if line.move_type == "reserve":
                    total_reserved += line.amount
                elif line.move_type == "obligate":
                    total_obligated += line.amount
                elif line.move_type == "consume":
                    total_consumed += line.amount

        reserved_pending = total_reserved - total_obligated
        obligated_pending = total_obligated - total_consumed

        return {
            "reserved_pending": max(0.0, reserved_pending),
            "obligated_pending": max(0.0, obligated_pending),
            "consumed": total_consumed,
            "total_used": total_reserved,
        }

    @api.model
    def _calculate_appropriated_amount(
        self, analytic_data, fiscal_year_id, company_id
    ):
        """Calculate total appropriated budget from budget moves"""
        domain = [
            ("state", "=", "posted"),
            ("move_type", "in", ("appropriation", "entry")),
            ("account_fiscal_year_id", "=", fiscal_year_id),
            ("company_id", "=", company_id),
        ]

        moves = self.env["budget.move"].search(domain)
        total = 0.0

        for move in moves:
            for line in move.line_ids:
                if self._line_matches_analytic_data(line, analytic_data):
                    total += line.balance

        return total

    @api.model
    def _calculate_reserved_amount(self, analytic_data, fiscal_year_id, company_id):
        """Calculate net reserved amount from active commitment lines.

        For active commitments: remaining lock = reserve lines - consume lines
        """
        active_commitments = self.env["budget.commitment"].search(
            [
                ("state", "in", ["reserved", "partial"]),
                ("account_fiscal_year_id", "=", fiscal_year_id),
                ("company_id", "=", company_id),
            ]
        )
        total = 0.0

        for commitment in active_commitments:
            posted = commitment.line_ids.filtered(lambda l: l.state == "posted")
            for line in posted.filtered(
                lambda l: l.move_type in ("reserve", "consume")
            ):
                if self._commitment_line_matches_analytic_data(line, analytic_data):
                    if line.move_type == "reserve":
                        total += line.amount
                    elif line.move_type == "consume":
                        total -= line.amount

        return max(0.0, total)

    @api.model
    def _calculate_consumed_amount(self, analytic_data, fiscal_year_id, company_id):
        """Calculate total consumed from ALL commitments (including done)"""
        commitments = self.env["budget.commitment"].search(
            [
                ("state", "in", ["reserved", "partial", "done"]),
                ("account_fiscal_year_id", "=", fiscal_year_id),
                ("company_id", "=", company_id),
            ]
        )
        total = 0.0

        for commitment in commitments:
            for line in commitment.line_ids.filtered(
                lambda l: l.state == "posted" and l.move_type == "consume"
            ):
                if self._commitment_line_matches_analytic_data(line, analytic_data):
                    total += line.amount

        return total

    @api.model
    def _commitment_line_matches_analytic_data(self, line, analytic_data):
        """Check if commitment line matches analytic data (exact match)"""
        if line.account_id.id != analytic_data.get("account_id"):
            return False

        # Department and source come from the header
        header_dept = (
            line.department_analytic_id.id if line.department_analytic_id else False
        )
        header_source = (
            line.source_analytic_id.id if line.source_analytic_id else False
        )
        if header_dept != analytic_data.get("department_analytic_id"):
            return False
        if header_source != analytic_data.get("source_analytic_id"):
            return False

        # Activity and fund from line's analytic_distribution
        line_activity = (
            line.activity_analytic_id.id if line.activity_analytic_id else False
        )
        line_fund = line.fund_analytic_id.id if line.fund_analytic_id else False
        if line_activity != analytic_data.get("activity_analytic_id"):
            return False
        if line_fund != analytic_data.get("fund_analytic_id"):
            return False

        return True

    @api.model
    def _line_matches_analytic_data(self, line, analytic_data):
        """Check if budget move line matches the given analytic data"""
        if line.account_id.id != analytic_data.get("account_id"):
            return False
        if line.source_analytic_id.id != analytic_data.get(
            "source_analytic_id", False
        ):
            return False

        # Hierarchical match for other dimensions
        if not self._analytic_matches_hierarchical(
            line.activity_analytic_id.id if line.activity_analytic_id else False,
            analytic_data.get("activity_analytic_id", False),
        ):
            return False

        if not self._analytic_matches_hierarchical(
            line.department_analytic_id.id if line.department_analytic_id else False,
            analytic_data.get("department_analytic_id", False),
        ):
            return False

        if not self._analytic_matches_hierarchical(
            line.fund_analytic_id.id if line.fund_analytic_id else False,
            analytic_data.get("fund_analytic_id", False),
        ):
            return False

        return True

    def _analytic_matches_hierarchical(self, parent_id, child_id):
        """Check if analytic accounts match hierarchically"""
        if not parent_id and not child_id:
            return True
        if not parent_id or not child_id:
            return False
        if parent_id == child_id:
            return True

        child_account = self.env["account.analytic.account"].browse(child_id)
        if child_account.exists() and child_account.parent_path:
            parent_ids = [
                int(id_str)
                for id_str in child_account.parent_path.strip("/").split("/")
                if id_str.isdigit()
            ]
            return parent_id in parent_ids

        return False

    def _format_budget_shortage_message(
        self, analytic_data, available_amount, requested_amount
    ):
        """Format detailed budget shortage error message"""
        account = self.env["budget.account"].browse(
            analytic_data.get("account_id")
        )
        activity = self.env["account.analytic.account"].browse(
            analytic_data.get("activity_analytic_id")
        )
        department = self.env["account.analytic.account"].browse(
            analytic_data.get("department_analytic_id")
        )
        fund = self.env["account.analytic.account"].browse(
            analytic_data.get("fund_analytic_id")
        )
        source = self.env["account.analytic.account"].browse(
            analytic_data.get("source_analytic_id")
        )

        return _(
            "Insufficient budget available:\n"
            "- Budget Account: %(account)s\n"
            "- Activity: %(activity)s\n"
            "- Department: %(department)s\n"
            "- Fund: %(fund)s\n"
            "- Source: %(source)s\n"
            "- Available: %(available).2f\n"
            "- Requested: %(requested).2f\n"
            "- Shortage: %(shortage).2f"
        ) % {
            "account": account.display_name if account else "N/A",
            "activity": activity.display_name if activity else "N/A",
            "department": department.display_name if department else "N/A",
            "fund": fund.display_name if fund else "N/A",
            "source": source.display_name if source else "N/A",
            "available": available_amount,
            "requested": requested_amount,
            "shortage": requested_amount - available_amount,
        }

    @api.model
    def _prepare_service_commitment_data(
        self, analytic_data, amount, fiscal_year_id, source_record, company_id
    ):
        """Prepare commitment data for service-created commitments"""
        commitment_name = _("Service Commitment")
        if source_record:
            commitment_name = _("Commitment for %s") % (
                getattr(source_record, "name", None)
                or "%s #%s" % (source_record._description, source_record.id)
            )

        # Build analytic_distribution for the line
        analytic_dist = {}
        if analytic_data.get("activity_analytic_id"):
            analytic_dist[str(analytic_data["activity_analytic_id"])] = 100.0
        if analytic_data.get("fund_analytic_id"):
            analytic_dist[str(analytic_data["fund_analytic_id"])] = 100.0

        line_vals = {
            "move_type": "reserve",
            "account_id": analytic_data.get("account_id"),
            "analytic_distribution": analytic_dist or False,
            "amount": amount,
            "name": _("Service reservation for %s")
            % (source_record._name if source_record else "system"),
        }

        # Build header analytic_distribution (department + source)
        header_dist = {}
        if analytic_data.get("department_analytic_id"):
            header_dist[str(analytic_data["department_analytic_id"])] = 100.0
        if analytic_data.get("source_analytic_id"):
            header_dist[str(analytic_data["source_analytic_id"])] = 100.0

        return {
            "name": commitment_name,
            "date": fields.Date.today(),
            "analytic_distribution": header_dist or False,
            "account_fiscal_year_id": fiscal_year_id,
            "company_id": company_id,
            "currency_id": self.env.company.currency_id.id,
            "amount": amount,
            "line_ids": [(0, 0, line_vals)],
        }

    @api.model
    def get_multi_line_budget_status(
        self, line_data_list, fiscal_year_id, company_id=None
    ):
        """Get budget status for multiple budget lines at once"""
        if not company_id:
            company_id = self.env.company.id

        grouped_lines = defaultdict(list)
        for idx, line_data in enumerate(line_data_list):
            key = self._get_analytic_key(line_data)
            grouped_lines[key].append((idx, line_data))

        results = {}

        for key, lines in grouped_lines.items():
            analytic_data = lines[0][1]
            budget_status = self.get_budget_status(
                analytic_data, fiscal_year_id, company_id
            )

            for idx, line_data in lines:
                results[idx] = budget_status.copy()

        return results

    @api.model
    def _get_analytic_key(self, analytic_data):
        """Get unique key for analytic combination"""
        return (
            analytic_data.get("account_id"),
            analytic_data.get("activity_analytic_id"),
            analytic_data.get("department_analytic_id"),
            analytic_data.get("fund_analytic_id"),
            analytic_data.get("source_analytic_id"),
        )
