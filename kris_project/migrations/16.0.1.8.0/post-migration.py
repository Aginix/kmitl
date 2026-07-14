"""Remap ir_attachment.document_type_id from the removed kris.project.document.type
model to the new base ir.attachment.document.type records.

- Runs post-migration so the new records (loaded from
  kris_project/data/kris_project_document_type_data.xml under
  ir.attachment.document.type) already exist.
- Reads the legacy kris_project_document_type table (Odoo leaves the table
  orphaned when its model class disappears from the registry) to build a
  per-attachment (old_name → attachment_ids) index, then rewrites
  ir_attachment.document_type_id to the new record chosen by NAME lookup
  via xmlid.
- Drops the legacy table afterwards so subsequent upgrades stay clean.
"""

import logging
from collections import defaultdict

from odoo import SUPERUSER_ID
from odoo.api import Environment

_logger = logging.getLogger(__name__)

# Legacy doctype `name` → xmlid of the replacement ir.attachment.document.type
NAME_TO_NEW_XMLID = {
    "เอกสารเบิกจ่ายและใบเสร็จ": "kris_project.doctype_receipt",
    "จัดซื้อจัดจ้าง": "kris_project.doctype_purchase",
    "สัญญา": "kris_project.doctype_contract",
}


def _legacy_table_exists(cr):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'kris_project_document_type'
        )
        """
    )
    return cr.fetchone()[0]


def migrate(cr, version):
    if not version:
        return

    if not _legacy_table_exists(cr):
        _logger.info(
            "kris_project migration: legacy table gone, nothing to remap"
        )
        return

    cr.execute(
        """
        SELECT ia.id, kdt.name
        FROM ir_attachment ia
        JOIN kris_project_document_type kdt
          ON ia.document_type_id = kdt.id
        """
    )
    rows = cr.fetchall()
    if not rows:
        cr.execute("DROP TABLE IF EXISTS kris_project_document_type CASCADE")
        return

    by_name = defaultdict(list)
    for att_id, name in rows:
        by_name[name].append(att_id)

    env = Environment(cr, SUPERUSER_ID, {})
    for name, att_ids in by_name.items():
        xmlid = NAME_TO_NEW_XMLID.get(name)
        if not xmlid:
            _logger.warning(
                "kris_project migration: no mapping for legacy doctype %r — "
                "%s attachments will lose their type",
                name,
                len(att_ids),
            )
            continue
        try:
            new_rec = env.ref(xmlid)
        except ValueError:
            _logger.warning(
                "kris_project migration: xmlid %s missing", xmlid
            )
            continue
        cr.execute(
            "UPDATE ir_attachment SET document_type_id = %s "
            "WHERE id = ANY(%s)",
            (new_rec.id, att_ids),
        )
        _logger.info(
            "kris_project migration: remapped %s attachments to %s",
            len(att_ids),
            xmlid,
        )

    cr.execute("DROP TABLE IF EXISTS kris_project_document_type CASCADE")
    _logger.info(
        "kris_project migration: legacy kris_project_document_type table dropped"
    )
