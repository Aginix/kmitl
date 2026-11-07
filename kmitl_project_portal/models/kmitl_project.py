from odoo import models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _portal_budget_tree(self, budget_type):
        """Flat render plan for the portal budget table, grouped into nested
        ประเภทงบ (project.budget.category) sections — mirrors the backend OWL tree
        (see static ``project_budget_table``). Returns an ordered list of rows::

            {"type": "header", "level": int, "name": str, "total": float}
            {"type": "line",   "level": int, "line": project.budget.line}

        The ancestry of each line is read from its ``category_parent_path`` (ids)
        and ``category_complete_name`` (labels); a header opens whenever the path
        diverges going down and carries the roll-up subtotal of its whole subtree.
        Lines are ordered so every subtree is contiguous and category-less lines
        (e.g. รายรับ, which carry no ประเภทงบ) fall at the end as flat rows.
        """
        self.ensure_one()
        lines = (
            self.expense_line_ids if budget_type == "expense" else self.income_line_ids
        )

        def chain(line):
            # [(id, name), ...] root-first; zips the id path with the "/"-joined
            # complete name (names are curated master data, free of " / ").
            ids = [p for p in (line.category_parent_path or "").split("/") if p]
            names = (
                line.category_complete_name.split(" / ")
                if line.category_complete_name
                else []
            )
            return list(zip(ids, names))

        def sort_key(line):
            ids = [int(p) for p in (line.category_parent_path or "").split("/") if p]
            return (0 if ids else 1, ids, line.sequence, line.id)

        lines = lines.sorted(key=sort_key)

        # Roll-up subtotal per node: every line adds its amount to each ancestor.
        totals = {}
        for line in lines:
            for cid, _name in chain(line):
                totals[cid] = totals.get(cid, 0.0) + line.amount

        rows = []
        prev = []
        for line in lines:
            ch = chain(line)
            common = 0
            while (
                common < len(prev)
                and common < len(ch)
                and prev[common][0] == ch[common][0]
            ):
                common += 1
            for level in range(common, len(ch)):
                cid, name = ch[level]
                rows.append(
                    {
                        "type": "header",
                        "level": level,
                        "name": name,
                        "total": totals.get(cid, 0.0),
                    }
                )
            rows.append({"type": "line", "level": len(ch), "line": line})
            prev = ch
        return rows
