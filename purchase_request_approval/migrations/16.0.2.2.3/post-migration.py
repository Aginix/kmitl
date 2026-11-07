# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration: คำนวณ ``estimated_cost`` ของ purchase.request.approval ใหม่
ให้ตรงกับ purchase.request (price_unit * product_qty ไม่บวก VAT แยก) — ตาม #1648

ทำเฉพาะ PA ที่ยอดไม่ตรงกับ PR ต้นทาง: PR เก่าที่สร้างก่อน #1648 ยังเก็บค่าเดิม
(รวม VAT) ไว้ และ PA ของ PR เหล่านั้นตรงกันอยู่แล้ว ถ้าคำนวณใหม่ทั้งหมดจะกลับไม่ตรง
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT pa.id
          FROM purchase_request_approval pa
          JOIN purchase_request pr ON pr.id = pa.request_id
         WHERE pa.estimated_cost IS DISTINCT FROM pr.estimated_cost
        """
    )
    pa_ids = tuple(r[0] for r in cr.fetchall())
    if not pa_ids:
        return
    cr.execute(
        """
        UPDATE purchase_request_approval_line
           SET estimated_cost = ROUND(
               (COALESCE(price_unit, 0) * COALESCE(product_qty, 0))::numeric, 2
           )
         WHERE approval_id IN %s
        """,
        (pa_ids,),
    )
    cr.execute(
        """
        UPDATE purchase_request_approval pa
           SET estimated_cost = COALESCE(
               (SELECT SUM(l.estimated_cost)
                  FROM purchase_request_approval_line l
                 WHERE l.approval_id = pa.id),
               0
           )
         WHERE pa.id IN %s
        """,
        (pa_ids,),
    )
    _logger.info("Recomputed estimated_cost on %s PAs: %s", len(pa_ids), pa_ids)
