from odoo import models


class Base(models.AbstractModel):
    _inherit = "base"

    def _annotation_is_locked(self):
        """Whether the files of this record carry a Locked layer: nobody may
        add, change or remove their annotations any more.

        Never by default; the module of a record overrides it, e.g. once the
        record is done, and may look at ``self.env.user`` to let some users
        through.
        """
        self.ensure_one()
        return False
