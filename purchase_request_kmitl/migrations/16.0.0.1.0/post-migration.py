"""Migrate ir_attachment.attachment_type (Selection: tor/rfq/etc) to
ir_attachment.document_type_id → ir.attachment.document.type records.

- The Selection field `attachment_type` is removed from
  purchase_request_kmitl in this version. The `attachment_type` column
  on ir_attachment is left behind by ORM until manually dropped.
- Read remaining values, remap by string key to xmlids created via
  purchase_request_kmitl/data/attachment_document_type.xml (loaded
  before this post-migration script), then UPDATE
  ir_attachment.document_type_id.
- Finally, DROP the orphan attachment_type column so it doesn't linger.
"""

import logging
from collections import defaultdict

from odoo import SUPERUSER_ID
from odoo.api import Environment

_logger = logging.getLogger(__name__)

VALUE_TO_NEW_XMLID = {
    "tor": "purchase_request_kmitl.doctype_tor",
    "rfq": "purchase_request_kmitl.doctype_rfq",
    "etc": "purchase_request_kmitl.doctype_etc",
}


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        )
        """,
        (table, column),
    )
    return cr.fetchone()[0]


def migrate(cr, version):
    if not version:
        return

    if not _column_exists(cr, "ir_attachment", "attachment_type"):
        _logger.info(
            "purchase_request_kmitl migration: attachment_type column "
            "already dropped, nothing to remap"
        )
        return

    cr.execute(
        """
        SELECT id, attachment_type
        FROM ir_attachment
        WHERE attachment_type IS NOT NULL
        """
    )
    rows = cr.fetchall()
    if not rows:
        cr.execute("ALTER TABLE ir_attachment DROP COLUMN attachment_type")
        return

    by_value = defaultdict(list)
    for att_id, value in rows:
        by_value[value].append(att_id)

    env = Environment(cr, SUPERUSER_ID, {})
    for value, att_ids in by_value.items():
        xmlid = VALUE_TO_NEW_XMLID.get(value)
        if not xmlid:
            _logger.warning(
                "purchase_request_kmitl migration: no mapping for %r — "
                "%s attachments will lose their type",
                value,
                len(att_ids),
            )
            continue
        try:
            new_rec = env.ref(xmlid)
        except ValueError:
            _logger.warning(
                "purchase_request_kmitl migration: xmlid %s missing", xmlid
            )
            continue
        cr.execute(
            "UPDATE ir_attachment SET document_type_id = %s "
            "WHERE id = ANY(%s)",
            (new_rec.id, att_ids),
        )
        _logger.info(
            "purchase_request_kmitl migration: remapped %s attachments "
            "from attachment_type=%r → %s",
            len(att_ids),
            value,
            xmlid,
        )

    cr.execute("ALTER TABLE ir_attachment DROP COLUMN attachment_type")
    _logger.info(
        "purchase_request_kmitl migration: orphan attachment_type column dropped"
    )
