# AGX Sarabun Module Documentation

## Overview

AGX Sarabun เป็นระบบจัดการเอกสารอิเล็กทรอนิกส์ (e-Sarabun) สำหรับ Odoo 16.0 รองรับการส่งเอกสาร, การกำหนดเส้นทางอนุมัติ, และการติดตามสถานะเอกสาร

## Integration Guide

### การเชื่อมต่อจากโมเดลอื่น

โมเดลอื่นๆ สามารถสร้างเอกสาร Sarabun และผูกกับ record ต้นทางได้ โดยใช้ `origin_model` และ `origin_res_id`

#### ตัวอย่าง: Purchase Request Integration

```python
# purchase_request.py
from odoo import models, fields, api, _

class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Request Number")
    amount_total = fields.Float(string="Total Amount")
    is_urgent = fields.Boolean(string="Urgent")
    state = fields.Selection([
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="draft")

    # Link to Sarabun document
    sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Sarabun Document",
        readonly=True,
    )

    def action_submit_for_approval(self):
        """Submit PR and create Sarabun document for routing"""
        self.ensure_one()

        # Get document type for internal memo
        doc_type = self.env.ref("agx_sarabun.document_type_internal", raise_if_not_found=False)
        if not doc_type:
            doc_type = self.env["sarabun.document.type"].search([("code", "=", "internal")], limit=1)

        # Create Sarabun document
        sarabun_doc = self.env["sarabun.document"].create({
            "document_type_id": doc_type.id,
            "subject": f"ขออนุมัติจัดซื้อ: {self.name}",
            "origin_model": self._name,
            "origin_res_id": self.id,
        })

        self.sarabun_document_id = sarabun_doc.id
        self.state = "pending_approval"

        # Auto-select route (opens wizard if multiple routes match)
        return sarabun_doc.action_select_route()

    # === Callback Methods (called by Sarabun) ===

    def _on_sarabun_completed(self, sarabun_doc):
        """Called when all routing is completed (approved)"""
        self.state = "approved"
        self.message_post(
            body=_("Purchase Request approved via Sarabun document %s") % sarabun_doc.name,
        )

    def _on_sarabun_rejected(self, sarabun_doc, recipient):
        """Called when document is rejected"""
        self.state = "rejected"
        self.message_post(
            body=_("Purchase Request rejected by %s. Reason: %s") % (
                recipient.actioned_by.name,
                recipient.comment or _("No reason provided"),
            ),
        )
```

### Callback Methods

เมื่อเอกสาร Sarabun ดำเนินการเสร็จ จะเรียก callback methods บน origin record:

| Method | เมื่อไหร่ | Parameters |
|--------|----------|------------|
| `_on_sarabun_completed(sarabun_doc)` | เมื่อ routing ครบทุกขั้นตอน | `sarabun_doc`: เอกสาร Sarabun |
| `_on_sarabun_rejected(sarabun_doc, recipient)` | เมื่อมีการ reject | `sarabun_doc`: เอกสาร Sarabun, `recipient`: ผู้ reject |

---

## Route Template Configuration

### การตั้งค่า Route Template

Route Template ใช้กำหนดเส้นทางเอกสารล่วงหน้า โดยสามารถกำหนด scope และ condition ได้

#### Scope Fields

| Field | คำอธิบาย |
|-------|----------|
| `department_id` | ใช้เฉพาะหน่วยงานที่ระบุ |
| `document_type_id` | ใช้เฉพาะประเภทเอกสารที่ระบุ |
| `origin_model` | ใช้เฉพาะเอกสารจาก model ที่ระบุ (e.g., `purchase.request`) |

#### Condition Domain

ใช้ Python domain expression เพื่อ filter ตามเงื่อนไขของ origin record:

```python
# ตัวอย่าง condition_domain

# จำนวนเงิน >= 100,000
[('amount_total', '>=', 100000)]

# จำนวนเงิน < 100,000
[('amount_total', '<', 100000)]

# เอกสารด่วน
[('is_urgent', '=', True)]

# หลายเงื่อนไขร่วมกัน (AND)
[('amount_total', '>=', 100000), ('is_urgent', '=', True)]

# เงื่อนไข OR
['|', ('amount_total', '>=', 500000), ('is_urgent', '=', True)]
```

### ตัวอย่างการตั้งค่า

#### Scenario: Purchase Request มี 3 เส้นทาง

**Template 1: PR มูลค่าต่ำกว่า 100,000**
```
Name: PR Approval (< 100k)
Origin Model: purchase.request
Condition Domain: [('amount_total', '<', 100000)]
Sequence: 10

Route Steps:
1. Department Head (Acknowledge)
2. Procurement (Acknowledge)
```

**Template 2: PR มูลค่า 100,000 - 500,000**
```
Name: PR Approval (100k - 500k)
Origin Model: purchase.request
Condition Domain: [('amount_total', '>=', 100000), ('amount_total', '<', 500000)]
Sequence: 20

Route Steps:
1. Department Head (Acknowledge)
2. Division Director (Approve)
3. Procurement (Acknowledge)
```

**Template 3: PR มูลค่าสูงกว่า 500,000**
```
Name: PR Approval (>= 500k)
Origin Model: purchase.request
Condition Domain: [('amount_total', '>=', 500000)]
Sequence: 30

Route Steps:
1. Department Head (Acknowledge)
2. Division Director (Approve)
3. Vice President (Approve)
4. Procurement (Acknowledge)
```

### Route Matching Logic

เมื่อเรียก `action_select_route()`:

1. ค้นหา templates ที่ match scope (origin_model, department, document_type)
2. Filter ด้วย `condition_domain` โดย evaluate กับ origin record
3. **ถ้า match 1 template** → Apply อัตโนมัติ
4. **ถ้า match หลาย templates** → เปิด wizard ให้ user เลือก
5. **ถ้าไม่ match template ใดๆ** → แสดง error

---

## API Reference

### SarabunDocument Methods

#### `action_select_route()`
เลือก route template สำหรับเอกสาร

```python
# Returns: True (if single match) or wizard action dict (if multiple matches)
sarabun_doc.action_select_route()
```

#### `_apply_route_template(template)`
Apply route template ไปยังเอกสาร (ใช้ภายใน)

```python
template = self.env["sarabun.route.template"].browse(template_id)
sarabun_doc._apply_route_template(template)
```

#### `_get_matching_route_templates()`
ค้นหา route templates ที่ match กับเอกสาร

```python
templates = sarabun_doc._get_matching_route_templates()
# Returns: recordset of sarabun.route.template
```

### SarabunRouteTemplate Methods

#### `find_matching_templates(origin_record, department_id, document_type_id)`
ค้นหา templates ที่ match criteria

```python
templates = self.env["sarabun.route.template"].find_matching_templates(
    origin_record=purchase_request,  # Optional: origin record for condition eval
    department_id=10,                 # Optional: filter by department
    document_type_id=5,               # Optional: filter by document type
)
```

#### `match_origin_record(origin_record)`
ตรวจสอบว่า template match กับ origin record หรือไม่

```python
if template.match_origin_record(purchase_request):
    print("Template matches!")
```

---

## Recipient Types

### User
ส่งตรงถึง user ที่ระบุ

```python
{
    "recipient_type": "user",
    "user_id": user.id,
}
```

### Department
ส่งไปยังหน่วยงาน (Sarabun Officers หรือ Manager จะรับเอกสาร)

```python
{
    "recipient_type": "department",
    "department_id": department.id,
    "department_text": "ฝ่ายจัดซื้อ",  # Optional: display text
}
```

### Role
ส่งตาม role/ตำแหน่ง

```python
{
    "recipient_type": "role",
    "role_id": role.id,
}
```

---

## Workflow States

### Document States

| State | คำอธิบาย |
|-------|----------|
| `draft` | ร่าง - สามารถแก้ไขได้ |
| `sent` | ส่งแล้ว - กำลังดำเนินการตาม routing |
| `completed` | เสร็จสิ้น - routing ครบทุกขั้นตอน |
| `cancelled` | ยกเลิก - ยกเลิกในขั้นตอน draft เท่านั้น |

### Recipient States

| State | คำอธิบาย |
|-------|----------|
| `new` | รอดำเนินการ |
| `acknowledged` | รับทราบแล้ว |
| `approved` | อนุมัติแล้ว |
| `rejected` | ปฏิเสธ |

---

## Security

### Groups

| Group | คำอธิบาย |
|-------|----------|
| `group_sarabun_user` | ผู้ใช้ทั่วไป - สร้าง/ส่งเอกสาร |
| `group_sarabun_manager` | ผู้จัดการ - จัดการ templates และดูเอกสารทั้งหมด |

### Record Rules

- **Sender Access**: ผู้สร้างเอกสารเห็นเอกสารของตนเอง
- **Recipient Access**: ผู้รับเอกสารเห็นเอกสารที่ส่งถึงตน
- **Manager Access**: Manager เห็นเอกสารทั้งหมด
