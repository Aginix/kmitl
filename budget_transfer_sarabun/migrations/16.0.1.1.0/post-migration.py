from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Point ``sarabun_enclosure_attachment_id`` at the แบบ งปม.303 already
    enclosed on each transfer's live หนังสือ.

    Before this version the generated file was not tracked, so a letter
    re-sent after ตีกลับ/ดึงกลับ would get a second งปม.303 alongside the
    stale one instead of the existing file being re-rendered in place.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    Document = env["sarabun.document"]
    transfers = env["budget.transfer"].search(
        [("sarabun_enclosure_attachment_id", "=", False)]
    )
    for transfer in transfers:
        document = Document.search(
            [
                ("origin_model", "=", "budget.transfer"),
                ("origin_res_id", "=", transfer.id),
                ("state", "not in", ("rejected", "cancelled")),
            ],
            order="id desc",
            limit=1,
        )
        if not document:
            continue
        filename = "%s.pdf" % ((transfer.name or "budget-transfer").replace("/", "-"))
        attachment = document.enclosure_attachment_ids.filtered(
            lambda a, fname=filename: a.name == fname
        )[:1]
        if attachment:
            transfer.sarabun_enclosure_attachment_id = attachment
