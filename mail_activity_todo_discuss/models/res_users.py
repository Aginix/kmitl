from odoo import api, fields, models, modules
from odoo.tools import html2plaintext


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_my_todos(self, res_model=False, limit=100, read=False):
        """List payload for the Discuss Todo page.

        Default (``read=False``): the current user's open Todos as records
        (capped at ``limit``), earliest deadline first, each carrying its
        source-app icon and the detail fields the list renders. Reuses
        ``_my_todo_count_domain`` (from mail_activity_todo) so the page, the
        systray badge and the Todo app all select the same Todos. Pass
        ``res_model`` to drill into a single source app (matching a sidebar
        group); ``total_count`` then reflects that app.

        History (``read=True``): the Todos that have left my inbox — the ones I
        dismissed with Mark as Read (still-live ``mail.activity``) merged with
        the ones that were completed (``todo.log`` snapshots, ADR-0004), newest
        handled first. See ``_get_my_todo_history``.
        """
        if read:
            return self._get_my_todo_history(res_model=res_model, limit=limit)
        Activity = self.env["mail.activity"]
        domain = self._my_todo_count_domain()
        if res_model:
            domain = domain + [("res_model", "=", res_model)]
        total = Activity.search_count(domain)
        activities = Activity.search(
            domain, limit=limit, order="date_deadline asc, id desc"
        )
        icons = {}
        todos = [self._todo_activity_card(act, icons) for act in activities]
        return {"todos": todos, "total_count": total}

    # ------------------------------------------------------------------
    # History (read + completed) — the inbox's "already handled" complement
    # ------------------------------------------------------------------
    def _get_my_todo_history(self, res_model=False, limit=100):
        """Merge my read/dismissed Todos (live ``mail.activity``) with my
        completed Todos (``todo.log`` snapshots) into one list, newest handled
        first, capped at ``limit``.

        The two live in different tables — Mark as Read keeps the activity (with
        a per-user read receipt), completion unlinks it after logging to
        ``todo.log`` — so each row carries a ``kind`` ("read"/"done") and a
        ``key`` unique across both. ``todo.log`` visibility is already scoped to
        the user by record rules (own / completed-by-me / role-in-unit), so no
        extra ownership domain is needed for the completed side.
        """
        Activity = self.env["mail.activity"]
        Log = self.env["todo.log"]
        icons = {}

        read_domain = self._my_read_todo_domain()
        log_domain = []
        if res_model:
            read_domain = read_domain + [("res_model", "=", res_model)]
            log_domain = log_domain + [("res_model", "=", res_model)]

        read_total = Activity.search_count(read_domain)
        done_total = Log.search_count(log_domain)

        read_acts = Activity.search(read_domain, limit=limit, order="id desc")
        # read_date drives the merge order; fetched only for sorting, not display.
        reads = (
            self.env["todo.read"]
            .sudo()
            .search(
                [
                    ("activity_id", "in", read_acts.ids),
                    ("user_id", "=", self.env.uid),
                ]
            )
        )
        read_date_by_act = {r.activity_id.id: r.read_date for r in reads}

        done_logs = Log.search(
            log_domain, limit=limit, order="completed_date desc"
        )

        # (sort_key, card) pairs so read and done interleave by when they were
        # handled, regardless of which table they came from.
        dated = []
        for act in read_acts:
            card = self._todo_activity_card(act, icons)
            card.update({"kind": "read", "key": "read-%s" % act.id})
            dated.append((read_date_by_act.get(act.id) or act.create_date, card))
        for log in done_logs:
            card = self._todo_log_card(log, icons)
            card.update({"kind": "done", "key": "done-%s" % log.id})
            dated.append((log.completed_date or log.create_date, card))

        dated.sort(key=lambda pair: pair[0], reverse=True)
        return {
            "todos": [card for _, card in dated[:limit]],
            "total_count": read_total + done_total,
        }

    # ------------------------------------------------------------------
    # Card builders (one dict per list row) + shared icon cache
    # ------------------------------------------------------------------
    def _todo_model_icon(self, model_name, cache):
        """Source model's app icon, resolved once per model and memoised in
        ``cache``. try-guarded so an icon edge case never blanks the list."""
        if model_name not in cache:
            icon = False
            try:
                icon_module = self.env[model_name]._original_module
                icon = icon_module and modules.module.get_module_icon(icon_module)
            except Exception:  # never let an icon edge case blank the panel
                icon = False
            cache[model_name] = icon or False
        return cache[model_name]

    def _todo_activity_card(self, act, icon_cache):
        """List row for a live Todo (an open inbox item or a read/dismissed
        one)."""
        return {
            "id": act.id,
            "summary": (
                act.summary
                or act.res_name
                or act.activity_type_id.display_name
                or ""
            ),
            "res_name": act.res_name or "",
            "res_model": act.res_model,
            "res_id": act.res_id,
            # sudo: regular users cannot read ir.model (non-sensitive metadata);
            # without it the whole payload raises AccessError for non-admins and
            # the Discuss list shows nothing.
            "app": act.res_model_id.sudo().display_name or "",
            "icon": self._todo_model_icon(act.res_model, icon_cache)
            if act.res_model
            else False,
            "activity_type": act.activity_type_id.display_name or "",
            "todo_category": act.todo_category,
            "assigned": act.user_id.display_name or "",
            "note": html2plaintext(act.note)[:160] if act.note else "",
            "date_deadline": (
                fields.Date.to_string(act.date_deadline)
                if act.date_deadline
                else False
            ),
            "state": act.state,
            # Serialized UTC datetime; the client renders it as a locale-aware
            # relative time ("3 hours ago") and formats the tooltip.
            "create_date": (
                fields.Datetime.to_string(act.create_date)
                if act.create_date
                else False
            ),
            "create_uid": act.create_uid.display_name or "",
        }

    def _todo_log_card(self, log, icon_cache):
        """List row for a completed Todo snapshot (``todo.log``). The source
        activity is gone, so there is no note / live deadline / urgency state;
        the meta line shows completed-when/by instead of created-when/by."""
        return {
            "id": log.id,
            "summary": (
                log.summary
                or log.res_name
                or (
                    log.activity_type_id.display_name
                    if log.activity_type_id
                    else ""
                )
                or ""
            ),
            "res_name": log.res_name or "",
            "res_model": log.res_model,
            "res_id": log.res_id,
            "app": log.res_model_id.sudo().display_name or "",
            "icon": self._todo_model_icon(log.res_model, icon_cache)
            if log.res_model
            else False,
            "activity_type": (
                log.activity_type_id.display_name if log.activity_type_id else ""
            ),
            "todo_category": log.todo_category,
            "assigned": log.user_id.display_name or "",
            "note": "",
            "date_deadline": False,
            "state": False,
            # Serialized UTC datetime, rendered client-side as relative time.
            "completed_date": (
                fields.Datetime.to_string(log.completed_date)
                if log.completed_date
                else False
            ),
            "completed_by": log.completed_by.display_name or "",
        }
