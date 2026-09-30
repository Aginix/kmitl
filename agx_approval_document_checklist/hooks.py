import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """เติมรายการเอกสารแนบให้คำขอที่ค้างอยู่ในสถานะ approved ตอนติดตั้งโมดูล.

    การ top-up ใน approval.request.write ยิงเฉพาะตอนที่ state *เปลี่ยนเป็น*
    approved คำขอที่นั่งอยู่ใน approved อยู่ก่อนแล้วจึงเดินหน้าไป to_disburse
    โดยไม่เคยผ่าน write นั้นเลย — และ approved คือช่วงบันทึกค่าใช้จ่ายจริงที่คำขอ
    ค้างนานที่สุด จึงเป็นกลุ่มที่ต้องการรายการเอกสารมากที่สุด. ``category_id`` เป็น
    readonly หลังบันทึกแล้ว จึงไม่มี onchange มาช่วยย้อนหลังด้วย.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = env["approval.request"].search(
        [
            ("state", "=", "approved"),
            ("category_id", "!=", False),
            ("disbursement_document_ids", "=", False),
        ]
    )
    if requests:
        requests._sync_disbursement_documents()
        _logger.info(
            "Materialised disbursement document checklists on %s approved "
            "approval request(s)",
            len(requests),
        )
