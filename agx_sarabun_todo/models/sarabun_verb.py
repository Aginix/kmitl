from odoo import api, fields, models

from odoo.addons.mail_activity_todo.models.mail_activity import TODO_CATEGORIES


class SarabunVerb(models.Model):
    _inherit = "sarabun.verb"

    # compute/inverse rather than a writable related: a Sarabun Manager edits verbs
    # but has no write right on mail.activity.type, so the inverse writes via sudo.
    todo_category = fields.Selection(
        TODO_CATEGORIES,
        string="Todo Category",
        compute="_compute_todo_category",
        inverse="_inverse_todo_category",
        help="How this verb's Todo clears: Execution only by acting at the หนังสือ; "
        "Acknowledgement (or blank) also by 'Mark as Read'. Blank Todos are not "
        "kept in the 'Completed by me' history. Applies to newly raised Todos.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        verbs = super().create(vals_list)
        # The inverse ran inside super() before core created the owned type —
        # re-apply the category now that the type exists.
        for verb, vals in zip(verbs, vals_list):
            if vals.get("todo_category"):
                verb.todo_category = vals["todo_category"]
        return verbs

    @api.depends("activity_type_id.todo_category")
    def _compute_todo_category(self):
        for verb in self:
            verb.todo_category = verb.activity_type_id.todo_category

    def _inverse_todo_category(self):
        for verb in self.filtered("activity_type_id"):
            verb.activity_type_id.sudo().todo_category = verb.todo_category

    @api.model
    def _seed_todo_category(self):
        """Seed every existing verb (built-in AND admin-made, archived too) once with
        the category the retired two-type discriminator gave it (gating OR
        show_signature → execution) — ADR-0020. Verbs created later start blank."""
        verbs = self.with_context(active_test=False).search([])
        for verb in verbs.filtered("activity_type_id"):
            if verb.todo_category:
                continue
            acts = verb.gating or verb.show_signature
            verb.todo_category = "execution" if acts else "acknowledgement"
