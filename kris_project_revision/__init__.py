# -*- coding: utf-8 -*-
from . import models


def populate_unrevisioned_name(cr, registry):
    """Backfill unrevisioned_name on projects created before revisions existed."""
    cr.execute(
        "UPDATE kris_project SET unrevisioned_name = name "
        "WHERE unrevisioned_name IS NULL"
    )
