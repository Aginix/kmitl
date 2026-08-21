{
    "name": "Aginix Approval Sarabun Todos",
    "version": "16.0.1.0.0",
    "author": "Aginix Technologies",
    "website": "https://github.com/aginix/kmitl",
    "category": "Accounting",
    "summary": "ต่อยอด agx_approval_todo: เมื่อจองงบประมาณแล้วแจ้งผู้สร้างให้สร้างหนังสือ "
    "เพื่อส่งขออนุมัติ และแจ้ง FYI กลับเมื่อคำขอได้รับอนุมัติ",
    "depends": [
        "agx_approval_todo",
        "agx_approval_sarabun",
        # โมดูลนี้สร้าง base.automation records เอง จึงประกาศตรง ๆ ไม่พึ่ง
        # transitive ผ่าน agx_approval_todo.
        "base_automation",
    ],
    "data": [
        "data/mail_activity_type.xml",
        "data/base_automation.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
