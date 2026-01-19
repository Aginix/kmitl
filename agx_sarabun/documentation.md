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

---

## Using Sarabun Document Mixin

### Basic Usage

สำหรับโมเดลที่ต้องการสร้างเอกสาร Sarabun อย่างง่าย ให้ inherit `sarabun.document.mixin`:

```python
from odoo import models

class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "sarabun.document.mixin"]

    def _prepare_sarabun_document_vals(self):
        """Override to customize Sarabun document values"""
        vals = super()._prepare_sarabun_document_vals()
        vals.update({
            "subject": f"ขออนุมัติจัดซื้อ: {self.name}",
        })
        return vals

    def _get_sarabun_subject(self):
        """Override to customize default subject"""
        return f"Purchase Request: {self.name}"
```

### Mixin Fields

Mixin provides computed fields:

| Field | Type | คำอธิบาย |
|-------|------|----------|
| `sarabun_document_ids` | One2many (computed) | เอกสาร Sarabun ที่ผูกกับ record นี้ |
| `sarabun_document_count` | Integer (computed) | จำนวนเอกสาร Sarabun |

### Mixin Methods

| Method | คำอธิบาย |
|--------|----------|
| `action_create_sarabun_document()` | สร้างเอกสาร Sarabun และเปิด form |
| `action_view_sarabun_documents()` | ดูเอกสาร Sarabun ที่เกี่ยวข้อง |
| `_prepare_sarabun_document_vals()` | Override เพื่อกำหนดค่าเริ่มต้นของเอกสาร |
| `_get_sarabun_subject()` | Override เพื่อกำหนด subject เริ่มต้น |
| `_on_sarabun_completed(document)` | Callback เมื่อ routing เสร็จสิ้น |
| `_on_sarabun_rejected(document, recipient)` | Callback เมื่อถูก reject |
| `_get_sarabun_report_action()` | Override เพื่อ delegate report ไปยัง origin model |

---

## Report Delegation

### Concept

เมื่อ Sarabun Document ถูกสร้างจาก origin record (เช่น Purchase Request) คุณอาจต้องการให้ portal/print ใช้ report ของ origin model แทน report ของ Sarabun

### Implementation

Override `_get_sarabun_report_action()` ใน origin model:

```python
class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "sarabun.document.mixin"]

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request report"""
        return self.env.ref("purchase_request.action_report_purchase_request")
```

### How It Works

```
Portal/Print Request
    │
    ▼
sarabun_document._get_delegated_report_action()
    │
    ├── Has origin with _get_sarabun_report_action()
    │       │
    │       ├── Portal/Print → Use origin model's report (PDF/HTML)
    │       │
    │       └── Form View → Show iframe preview (hide Content tab)
    │
    └── No delegation
            │
            └── Use Sarabun's default report + Content tab
```

### Form View Behavior

เมื่อ origin model มี report delegation:

- **Content tab**: ซ่อนอัตโนมัติ
- **Document Preview tab**: แสดง report จาก origin เป็น iframe

### Benefits

- **Real-time data**: Report แสดงข้อมูลปัจจุบันของ origin record
- **No file attachment**: ไม่ต้อง generate และ attach PDF ล่วงหน้า
- **Single source of truth**: ใช้ report template เดียวกับ origin model
- **Inline preview**: ดู report ได้ในหน้าฟอร์มโดยไม่ต้องเปิด tab ใหม่

### Example: Complete Integration

```python
class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "sarabun.document.mixin"]

    def _prepare_sarabun_document_vals(self):
        """Customize Sarabun document creation"""
        vals = super()._prepare_sarabun_document_vals()
        vals.update({
            "subject": f"ขออนุมัติจัดซื้อ: {self.name} ({self.amount_total:,.0f} บาท)",
        })
        return vals

    def _get_sarabun_report_action(self):
        """Use Purchase Request report in Sarabun portal"""
        return self.env.ref("purchase_request.action_report_purchase_request")

    def _on_sarabun_completed(self, document):
        """Auto-approve when Sarabun routing completes"""
        self.state = "approved"

    def _on_sarabun_rejected(self, document, recipient):
        """Handle rejection"""
        self.state = "rejected"
```

เมื่อ user เปิด Sarabun Document ที่สร้างจาก Purchase Request:
- หน้า Portal จะแสดง report ของ Purchase Request
- กด Download PDF จะได้ไฟล์ของ Purchase Request
- ข้อมูลเป็นปัจจุบันเสมอ (real-time rendering)
