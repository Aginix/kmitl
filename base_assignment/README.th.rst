========================================
Base Assignment (มอบหมายเจ้าหน้าที่)
========================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
    :alt: License: LGPL-3
.. |badge3| image:: https://img.shields.io/badge/language-en-red.png
    :target: README.rst
    :alt: Read in English

|badge1| |badge2| |badge3|

Mixin กลางสำหรับการมอบหมาย **เจ้าหน้าที่ผู้รับผิดชอบ** (Assigned Officer) —
โมดูล consumer ที่ ``_inherit`` mixin นี้จะได้ **alert box + ปุ่ม 3 ปุ่ม**
(มอบหมายให้ฉัน / มอบหมายให้… / ยกเลิกการมอบหมาย) โผล่เหนือ ``<sheet>``
ของฟอร์มโดยอัตโนมัติ — โดยที่ **ไม่ต้องแก้ XML view** ของตัวเอง และปุ่ม
พวกนี้ไม่ปนกับปุ่ม workflow ใน header ของฟอร์ม

**สารบัญ**

.. contents::
   :local:

รายละเอียด (Description)
========================

Business document หลายตัวต้อง track **เจ้าหน้าที่ผู้รับผิดชอบ** — คนที่กำลัง
รับผิดชอบผลักดันเอกสารตัวนั้น ๆ ให้เดินหน้า ถ้าไม่มีโมดูลกลาง แต่ละโมดูลที่
ต้องการฟีเจอร์นี้ก็ต้อง copy-paste ปุ่ม 3 ปุ่ม (Assign to me / Assign… /
Unassign), wizard เดียวกัน, และ activity To-Do แจ้งเตือนแบบเดียวกัน ทุก
ครั้งที่ต้องแก้อะไรก็ต้องเดินไปแก้ทุกจุด

โมดูลนี้แก้ปัญหาด้วยการรวมเป็น ``AbstractModel`` ตัวเดียว
(``assignment.mixin``) พร้อม QWeb template ที่ Odoo **inject อัตโนมัติ**
เหนือ ``<sheet>`` ของฟอร์ม consumer — pattern เดียวกับ
``base_tier_validation`` — consumer แค่ ``_inherit`` mixin, ประกาศ
2 กลุ่ม (officer + manager), และ field ``assigned_to`` เท่านั้น

**หมายเหตุ:** โมดูลนี้ **ไม่มีฟีเจอร์สำหรับผู้ใช้งาน (end-user)** ของตัวเอง
เป็นแค่ **โมดูลกลาง (foundation)** ให้โมดูลอื่น inherit ไปใช้

อ้างอิงตัวอย่างการใช้งานจริงในโปรเจ็กต์นี้:

* ``procurement_assignment_kmitl`` — ใช้กับ purchase.request, purchase.order
* ``disbursement`` — ใช้กับ disbursement.request (พร้อม routing rules)

การตั้งค่า (Configuration)
==========================

``base_assignment`` **ไม่มี Settings UI** ของตัวเอง — consumer แต่ละตัว
เป็นเจ้าของ toggle "takeover" ของตัวเอง โดยระบุ ``ir.config_parameter``
key ผ่าน method ``_assignment_takeover_param()`` และเลือก default ผ่าน
``_assignment_takeover_default()``

Toggle นี้ตอบคำถามเดียว: **"เมื่อเอกสารถูกมอบหมายให้คนหนึ่งไปแล้ว
เจ้าหน้าที่คนอื่นสามารถกด *มอบหมายให้ฉัน* เพื่อแย่งได้ไหม?"** ถ้าปิด —
การมอบหมายใหม่ต้องผ่าน manager (ปุ่ม *มอบหมายให้…*) ถ้าเปิด — เจ้าหน้าที่
ในกลุ่ม officer คนไหนก็แย่งได้

ตัวอย่างใน repository:

* ``procurement_assignment_kmitl`` — parameter
  ``procurement_assignment_kmitl.allow_takeover_assigned`` (default
  ``False`` — เข้มงวด: manager เท่านั้นที่ reassign ได้) มี Settings toggle
  ในหน้าตั้งค่าของ Purchase

* ``disbursement`` — parameter ``disbursement.allow_takeover_assigned``
  (default ``True`` — advisory: officer แย่งใบที่ routing ผิดได้ทันที)

ถ้า consumer ไม่ต้องการฟีเจอร์ takeover ให้ ``_assignment_takeover_param()``
return ``None`` — จะกลายเป็น: self-claim ทำได้เฉพาะเอกสารที่ยังไม่ถูก
มอบหมาย, และการ reassign ทั้งหมดต้องผ่าน manager

การใช้งาน (Usage)
=================

เพิ่มการมอบหมายเจ้าหน้าที่เข้ากับ document ใหม่
-----------------------------------------------

#. เพิ่ม ``base_assignment`` เข้า ``depends`` ของโมดูล
#. ``_inherit`` ``assignment.mixin`` **พร้อมกับ** ``mail.activity.mixin``
   ใน model target (mixin ใช้ ``activity_ids`` และ ``activity_schedule``
   ตอน runtime แต่ไม่ inherit มาโดยตรงเพื่อกัน MRO conflict —
   ดูรายละเอียดใน ADR-0001)
#. **ประกาศ field ``assigned_to`` เอง** เพื่อให้ attributes ของ field
   (เช่น ``tracking``, ``copy``, ``groups``) ที่มีอยู่แล้วในโมดูลไม่โดนทับ
#. Set 2 class attributes บอก mixin ว่าใครคือ officer และใครคือ manager

Consumer ขั้นต่ำ:

.. code-block:: python

    from odoo import fields, models


    class MyDoc(models.Model):
        _name = "my.doc"
        _inherit = ["my.doc", "mail.activity.mixin", "assignment.mixin"]

        _assign_user_group = "my_module.group_my_officer"
        _assign_manager_group = "my_module.group_my_manager"

        assigned_to = fields.Many2one(
            "res.users",
            string="Assigned Officer",
            tracking=True,
        )

เท่านี้ก็จะได้ alert เหนือ sheet พร้อมปุ่ม 3 ปุ่ม ที่ respect กลุ่ม
officer / manager ของ consumer

จุดขยาย (Extension points)
--------------------------

Class attributes (อ่านตอน render view):

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Attribute
     - Default
     - Purpose
   * - ``_assign_user_group``
     - ``None`` (จำเป็น)
     - xmlid กลุ่มที่ claim ได้
   * - ``_assign_manager_group``
     - ``None`` (จำเป็น)
     - xmlid กลุ่มที่ reassign / unassign ได้
   * - ``_assignment_manual_config``
     - ``False``
     - ``True`` = ปิด banner อัตโนมัติ
   * - ``_assignment_alert_xpath``
     - ``"/form/sheet"``
     - ตำแหน่งใน arch ที่ inject alert
   * - ``_assignment_alert_position``
     - ``"before"``
     - ``"before"`` / ``"after"`` / ``"inside"``

Method hooks (override ที่ consumer, optional ทุกตัว):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Hook
     - ค่า default
   * - ``_assignment_activity_xmlid()``
     - ``base_assignment.mail_activity_assignment``
   * - ``_assignment_activity_summary()``
     - ``_("Assigned as responsible officer")``
   * - ``_assignment_takeover_param()``
     - ``None`` — feature off
   * - ``_assignment_takeover_default()``
     - ``False``
   * - ``_assignment_on_assigned(new, old)``
     - ``None`` — no-op lifecycle hook
   * - ``_assignment_on_unassigned(old)``
     - ``None`` — no-op lifecycle hook

ย้าย alert ไปตำแหน่งอื่น
------------------------

override 2 class attributes — ไม่ต้อง override ``get_view``:

.. code-block:: python

    class MyDoc(models.Model):
        _inherit = ["my.doc", "mail.activity.mixin", "assignment.mixin"]
        _assignment_alert_xpath = "//div[@class='oe_title']"
        _assignment_alert_position = "before"

ปิด banner อัตโนมัติ
--------------------

Set ``_assignment_manual_config = True`` เมื่อฟอร์มของคุณมี card ของ
ตัวเองอยู่แล้ว หรือฟอร์มมีโครงสร้างพิเศษที่ default xpath ไม่ match —
Python API (``action_assignment_assign_me``, ``action_assignment_unassign``,
``action_assignment_open_wizard``) ยังใช้ได้ปกติสำหรับปุ่มใน header ที่
consumer สร้างเอง หรือเรียกผ่าน RPC:

.. code-block:: python

    class MyDoc(models.Model):
        _inherit = ["my.doc", "mail.activity.mixin", "assignment.mixin"]
        _assignment_manual_config = True

Hook lifecycle เพื่อรับ event เปลี่ยนการมอบหมาย
-------------------------------------------------

Override method hook เพื่อ trigger side effect โดยไม่ต้องเขียนทับ
action method:

.. code-block:: python

    def _assignment_on_assigned(self, new_user, old_user):
        # ส่ง email, เปลี่ยน state, log, ...
        self.message_post(
            body=_("Officer changed to %s") % new_user.display_name,
        )

    def _assignment_on_unassigned(self, old_user):
        self.message_post(body=_("Officer released."))

Hook ทั้งสองถูกเรียก **หลัง write เสร็จ** ดังนั้น ``self.assigned_to``
คือค่าใหม่แล้ว

Customize wizard reassign
-------------------------

Wizard model กลางชื่อ ``assign.officer.wizard`` — ถ้าอยากเพิ่ม field
(เช่น comment) ให้ inherit มัน:

.. code-block:: python

    class AssignOfficerWizard(models.TransientModel):
        _inherit = "assign.officer.wizard"

        comment = fields.Text()

ประเด็นที่รู้อยู่แล้ว / แผนพัฒนา
================================

Consumer ที่ใช้อยู่แล้ว
------------------------

* ``procurement_assignment_kmitl`` — purchase.request + purchase.order
  (consumer แบบบาง — override hooks เท่านั้น ไม่มี logic ธุรกิจเพิ่ม)
* ``disbursement`` — disbursement.request (มี routing rule engine
  ``disbursement.assignment.rule`` บวก return-for-correction workflow
  เฉพาะการตรวจสอบ)

โมดูลคู่กัน (Companion)
-----------------------

* ``base_assignment_todo`` — bridge แบบ data-only tag activity type ของ
  assignment ให้มี ``todo_category`` เพื่อโผล่ใน Todo inbox กลาง
  (``mail_activity_todo``)

Deferred (ยังไม่ทำ, เก็บเป็น issue)
------------------------------------

* **State gating** — class attribute ``_assignment_allowed_states``
  (คล้าย ``_state_from`` / ``_state_to`` ของ ``base_tier_validation``)
  ให้ consumer ระบุ "ให้ claim ได้เฉพาะใน state ``signed``" ตอนนี้
  consumer ที่ต้องการ ต้อง override ``action_assignment_assign_me``
  และ ``action_assign`` ของ wizard เอง
* **Base tests** — mixin ตัวเองยังไม่มี unit test ตรง ๆ (behavior
  ครอบคลุมโดย test ของ consumer 2 โมดูล) อนาคตควรเพิ่ม dummy
  TransientModel test เพื่อ catch regression ของ default hooks
* **Wizard field injection API** — Consumer สามารถ
  ``_inherit = "assign.officer.wizard"`` เพิ่ม field เองได้แล้ว
  (เช่น comment บังคับ) ไม่ได้ทำ API เฉพาะ

Credits
=======

Authors / ผู้พัฒนา
------------------

* Aginix Technologies
* KMITL (สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง)

Referenced work / งานที่อ้างอิง
--------------------------------

* OCA ``base_tier_validation`` — pattern ``get_view`` inject template
* OCA ``base_state_leadtime`` — convention ตั้งชื่อ ``base_*``
