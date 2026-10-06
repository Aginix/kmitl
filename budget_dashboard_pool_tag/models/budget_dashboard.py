from collections import defaultdict

from odoo import api, models


class BudgetDashboard(models.AbstractModel):
    """List Pool Tag items (โครงการ/แผน) under each budget code of the report.

    Generic engine: no tag is known here. The module that owns a Pool Tag
    registers it by overriding :meth:`_pool_tags` (``super()`` + append), the
    same open-for-extension shape as ``_overview_sections``.

    Items hang only under the budget code whose lines carry them (never rolled
    up to ancestor codes, which already include them in their own figures). Per
    code a residual "ไม่ระบุโครงการ/แผน" row carries the untagged remainder, so
    the item rows always add up to the code row's own figures.
    """

    _inherit = "budget.dashboard"

    _POOL_TAG_UNTAGGED_NAME = "ไม่ระบุโครงการ/แผน"

    def _pool_tags(self):
        """Registered Pool Tags, in display order.

        Each entry: ``{"field", "label", "toggle_label", "res_model",
        "res_field"}`` — ``field`` is the stored tag field on budget move /
        commitment lines; ``res_model`` / ``res_field`` locate the owning
        document (e.g. ``kmitl.project`` by ``analytic_account_id``).
        """
        return []

    @api.model
    def get_pool_tags(self):
        """Tag toggles for the front end: ``[{field, toggle_label}]``."""
        return [
            {"field": tag["field"], "toggle_label": tag["toggle_label"]}
            for tag in self._pool_tags()
        ]

    @api.model
    def get_pool_tag_rows(
        self,
        fiscal_year_id,
        root_account_id=None,
        filters=None,
        breakdown=None,
        tag_fields=None,
    ):
        """Item rows to hang under the report's budget-account rows.

        Same scope (fiscal year / category / dimension filters / breakdown) and
        same column sources as :meth:`get_dashboard_data`, grouped additionally
        by the enabled tag fields. Each row carries ``account_id`` and ``dims``
        (the breakdown tuple of the account row it belongs under); the front end
        splices it beneath that row.
        """
        tags = [t for t in self._pool_tags() if t["field"] in (tag_fields or [])]
        if not fiscal_year_id or not tags:
            return []
        accounts = self._dashboard_accounts(root_account_id)
        if not accounts:
            return []
        move_base, cl_base, commit_domain, _hier_op = self._dashboard_domains(
            fiscal_year_id, accounts.ids, filters or {}
        )
        dims = self._normalize_breakdown(breakdown) or []
        tag_names = [t["field"] for t in tags]
        all_dims = dims + tag_names

        sources = {
            "current": self._facts_by_account_dims(
                "budget.move.line",
                move_base + [("move_type", "in", ("appropriation", "entry"))],
                "balance",
                all_dims,
            ),
            "initial": self._facts_by_account_dims(
                "budget.move.line",
                move_base
                + [
                    ("move_type", "=", "appropriation"),
                    ("appropriation_type", "=", "initial"),
                ],
                "balance",
                all_dims,
            ),
            "cap": self._cap_facts_by_account_dims(commit_domain, all_dims),
            "returned": self._facts_by_account_dims(
                "budget.commitment.line",
                cl_base + [("is_return", "=", True)],
                "amount",
                all_dims,
            ),
        }
        by_type = self._facts_by_account_dims_type(
            "budget.commitment.line", cl_base, "amount", all_dims
        )
        sources["reserved"] = by_type.get("reserve", {})
        sources["obligated"] = by_type.get("obligate", {})
        sources["consumed"] = by_type.get("consume", {})

        # own[(account_id, breakdown_tuple)][(tag_field, analytic_id)] = values.
        # A line carrying two tags is assigned to the first one only, so no
        # amount is ever counted twice; (False, 0) is the untagged remainder.
        n = len(dims)
        own = defaultdict(dict)
        for metric, facts in sources.items():
            for (acc_id, tup), val in facts.items():
                item = (False, 0)
                for field, tag_id in zip(tag_names, tup[n:]):
                    if tag_id:
                        item = (field, tag_id)
                        break
                bucket = own[(acc_id, tup[:n])]
                vals = bucket.setdefault(item, dict.fromkeys(sources, 0.0))
                vals[metric] += val

        tagged_ids = {
            tag_id for bucket in own.values() for (field, tag_id) in bucket if field
        }
        analytic = {
            a.id: a
            for a in self.env["account.analytic.account"].browse(list(tagged_ids))
        }
        docs = self._pool_tag_documents(tags, tagged_ids)
        tag_order = {name: i for i, name in enumerate(tag_names)}

        rows = []
        for (acc_id, bd), bucket in own.items():
            if not any(field for field, _tag_id in bucket):
                continue  # nothing tagged on this code: no item rows
            items = sorted(
                bucket,
                key=lambda it: (
                    not it[0],  # untagged remainder last
                    tag_order.get(it[0], 0),
                    (analytic[it[1]].code or "") if it[0] else "",
                ),
            )
            for field, tag_id in items:
                rec = analytic.get(tag_id)
                res_model, res_id = docs.get(tag_id, (False, False))
                rows.append(
                    {
                        "row_type": "pool_tag",
                        "account_id": acc_id,
                        "dims": {dims[i]: (bd[i] or False) for i in range(n)},
                        "tag_field": field,
                        "analytic_id": tag_id or False,
                        "code": (rec.code or "") if rec else "",
                        "name": rec.name if rec else self._POOL_TAG_UNTAGGED_NAME,
                        "res_model": res_model,
                        "res_id": res_id,
                        "has_children": False,
                        **self._value_columns(bucket[(field, tag_id)]),
                    }
                )
        return rows

    def _pool_tag_documents(self, tags, analytic_ids):
        """analytic id -> (res_model, res_id) of the owning project / plan.

        Plain searches (never ``sudo``): a document the user cannot read is
        simply not linked, so its name renders as plain text.
        """
        out = {}
        if not analytic_ids:
            return out
        for tag in tags:
            model_name = tag.get("res_model")
            if not model_name or model_name not in self.env:
                continue
            Model = self.env[model_name]
            if not Model.check_access_rights("read", raise_exception=False):
                continue
            res_field = tag.get("res_field") or "analytic_account_id"
            for doc in Model.search([(res_field, "in", list(analytic_ids))]):
                out.setdefault(doc[res_field].id, (model_name, doc.id))
        return out
