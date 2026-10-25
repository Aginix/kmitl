import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# Arbitrary constant: one worker reflects the acts while the others skip.
_REFLECT_LOCK = 5782301


class WorkCenterAct(models.Model):
    """The act registry (ADR-0003).

    Acts are declared in Python by the capability module that implements them
    (``_work_center_acts`` on the document model) and reflected into these
    records, so a station can list which ones it allows and requires. Rows are
    never deleted: visits reference them as audit evidence, so an act that is
    no longer declared is archived instead.

    ``kind == 'edit'`` entries are not acts: they name a part of the document a
    station lets its people edit. They can never be required.
    """

    _name = "work.center.act"
    _description = "Station Act"
    _order = "sequence, id"

    code = fields.Char(
        required=True,
        index=True,
        readonly=True,
        help="Stable, module-agnostic identifier, e.g. disbursement.validate.",
    )
    name = fields.Char(required=True, translate=True, readonly=True)
    kind = fields.Selection(
        selection=[("act", "Act"), ("edit", "Editable Part")],
        required=True,
        default="act",
        readonly=True,
        help="An editable part is an edit permission on the document, not an "
        "act: it can never be required before a document is forwarded.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    model_name = fields.Char(related="model_id.model", store=True, index=True)
    group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Role",
        ondelete="set null",
        readonly=True,
        help="The role entitled to perform the act. An act without a role is "
        "offered to nobody.",
    )
    module = fields.Char(readonly=True, help="The module that declares the act.")
    sequence = fields.Integer(default=10, readonly=True)
    active = fields.Boolean(default=True, readonly=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The act code must be unique."),
    ]

    # ------------------------------------------------------------------
    # Reflection of the declared acts
    # ------------------------------------------------------------------
    def _register_hook(self):
        super()._register_hook()
        # Odoo runs this after every module has loaded its data. Only an
        # install or an upgrade changes what the code declares, so a plain
        # worker start (nothing updated) writes nothing.
        if not self.pool.updated_modules:
            return
        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(%s)", [_REFLECT_LOCK])
        if self.env.cr.fetchone()[0]:
            self.sudo()._reflect_acts()

    @api.model
    def _act_label(self, label):
        """Translate a lazy label in the language of ``self``'s context.

        ``_lt`` looks the language up in the frame that calls ``str()``, which
        is this one, so the label follows ``self.env.lang``.
        """
        return str(label)

    @api.model
    def _declared_acts(self):
        """Every act declared by a document model that carries the mixin, as
        (model name, declaration) pairs."""
        mixin = self.pool["work.center.mixin"]
        declared = []
        for model_name, model in self.env.items():
            if model._abstract or not issubclass(type(model), mixin):
                continue
            try:
                declared += [(model_name, decl) for decl in model._work_center_acts()]
            except Exception:  # pylint: disable=broad-except
                _logger.warning(
                    "Could not read the acts declared by %s", model_name, exc_info=True
                )
        return declared

    @api.model
    def _reflect_acts(self):
        """Mirror the declared acts into records: upsert by code, unarchive a
        re-declared code, archive the codes nobody declares any more."""
        acts = self.with_context(active_test=False).search([])
        by_code = {act.code: act for act in acts}
        languages = [code for code, _name in self.env["res.lang"].get_installed()]
        seen = set()
        for model_name, decl in self._declared_acts():
            code = decl.get("code")
            if not code:
                _logger.warning("An act of %s has no code; skipped", model_name)
                continue
            seen.add(code)
            try:
                with self.env.cr.savepoint():
                    self._reflect_act(by_code.get(code), model_name, decl, languages)
            except Exception:  # pylint: disable=broad-except
                _logger.warning("Could not reflect act %s", code, exc_info=True)
        for code, act in by_code.items():
            if code not in seen and act.active:
                act.active = False
        return True

    def _reflect_act(self, act, model_name, decl, languages):
        group = False
        if decl.get("group"):
            group = self.env.ref(decl["group"], raise_if_not_found=False)
            if not group:
                _logger.warning(
                    "Act %s: role %s does not exist; it is offered to nobody",
                    decl["code"],
                    decl["group"],
                )
        vals = {
            "kind": decl.get("kind", "act"),
            "model_id": self.env["ir.model"]._get(model_name).id,
            "group_id": group.id if group else False,
            "module": decl.get("module") or False,
            "sequence": decl.get("sequence", 10),
            "active": True,
        }
        # The source language first; the other languages follow below.
        name = self.with_context(lang="en_US")._act_label(decl["name"])
        if not act:
            act = self.create(dict(vals, code=decl["code"], name=name))
        else:
            changed = {
                field: value
                for field, value in vals.items()
                if act._fields[field].convert_to_write(act[field], act) != value
            }
            if changed:
                act.write(changed)
        # The name is translated for every installed language, because the
        # act is created from code and no .po reference can reach it.
        translations = {
            lang: self.with_context(lang=lang)._act_label(decl["name"])
            for lang in languages
        }
        if any(
            act.with_context(lang=lang).name != translated
            for lang, translated in translations.items()
        ):
            act.update_field_translations("name", translations)

    @api.model
    def action_sync_acts(self):
        """Manager shortcut for the same reflection the module upgrade runs.
        The registry is read-only for everyone, hence the explicit check."""
        if not self.env.user.has_group("work_center.group_work_center_manager"):
            raise AccessError(_("Only a Station Administrator can sync the acts."))
        self.sudo()._reflect_acts()
        return {"type": "ir.actions.client", "tag": "reload"}
