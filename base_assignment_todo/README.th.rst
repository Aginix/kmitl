=====================================================
Base Assignment Todos (แจ้งเตือนการมอบหมายใน Todo Inbox)
=====================================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/license-LGPL--3-blue.png
    :alt: License: LGPL-3
.. |badge3| image:: https://img.shields.io/badge/language-en-red.png
    :target: README.rst
    :alt: Read in English

|badge1| |badge2| |badge3|

โมดูล bridge เล็ก ๆ (data-only) — ทำให้แจ้งเตือนการมอบหมายเจ้าหน้าที่จาก
``base_assignment`` **โผล่ในหน้า Todo Inbox กลาง** ของ ``mail_activity_todo``
เจ้าหน้าที่จะเห็นงานที่รอตัวเองพร้อมกันในที่เดียว และปิดการแจ้งเตือนได้ด้วย
**Mark as Read**

**สารบัญ**

.. contents::
   :local:

รายละเอียด (Description)
========================

``base_assignment`` schedule activity type
``base_assignment.mail_activity_assignment`` บน record ทุกครั้งที่มีการ
มอบหมายเจ้าหน้าที่ — เพื่อแจ้งเตือนคนใหม่ที่รับผิดชอบ แต่ default ของ
activity type นี้**ไม่มี** ``todo_category`` ดังนั้นการแจ้งเตือน**ไม่โผล่**
ใน Todo Inbox กลางที่ ``mail_activity_todo`` จัดการอยู่ — เจ้าหน้าที่จะเห็น
แค่ activity บน chatter ของเอกสารเท่านั้น

โมดูลนี้เป็น **data-only bridge** — ตอน install/upgrade จะ tag activity
type ให้มี ``todo_category = "acknowledgement"`` → การแจ้งเตือนโผล่ใน
Todo Inbox และผู้รับปิดได้ด้วย **Mark as Read**

**ทำไมใช้ Acknowledgement ไม่ใช้ Execution หรือ Approval?**

Activity แจ้งเตือนการมอบหมายไม่มี state "done" ของตัวเอง — มันถูก unlink
เมื่อมีการ reassign หรือ unassign เท่านั้น ไม่ใช่ตอนที่เจ้าหน้าที่ทำอะไร
เสร็จสักขั้น Acknowledgement เป็น category ของ Todo ที่ **คาดหวังให้ผู้รับ
กด dismiss เอง (Mark as Read)** — เข้ากับ lifecycle นี้พอดี และมี retention
cron ที่ sweep acknowledgement ที่อ่านแล้วหลังพ้น threshold → inbox ไม่รก

การใช้งาน (Usage)
=================

โมดูลนี้**ไม่มี UI สำหรับผู้ใช้** และ**ไม่ต้องเขียนโค้ดเพิ่ม** — แค่ติดตั้ง

Prerequisites
-------------

* ``base_assignment`` และ consumer อย่างน้อย 1 ตัวที่ inherit
  ``assignment.mixin`` (เช่น ``procurement_assignment_kmitl`` หรือ
  ``disbursement`` ในโปรเจ็กต์นี้)
* ``mail_activity_todo`` — engine ของ Todo Inbox กลาง

หลังติดตั้ง
-----------

#. เปิดเมนู **Todo Inbox**
#. เจ้าหน้าที่ทุกคนจะเห็นการแจ้งเตือนการมอบหมายที่รอตัวเอง โผล่พร้อมกับ
   Todo อื่น ๆ (approvals, executions, FYIs)
#. Todo แต่ละอันปิดได้ด้วย **Mark as Read** — จะหายจาก inbox ของตัวเอง
   *เท่านั้น* ไม่กระทบ activity ที่อยู่บน chatter ของ source record
#. เมื่อมีการ reassign หรือ unassign ที่ source document — Todo ที่ตรงกันก็
   จะถูกเคลียร์อัตโนมัติ

ถอนการติดตั้ง
-------------

ถอนโมดูลนี้แค่**ลบ ``todo_category`` tag** ออกจาก activity type ของการ
มอบหมาย ตัว activity เอง กับโมดูล ``base_assignment`` ยังทำงานตามเดิม —
แค่ไม่มี integration กับ Todo Inbox แล้ว

ประเด็นที่รู้อยู่แล้ว / แผนพัฒนา
================================

Deferred (ยังไม่ทำ)
-------------------

* **auto_install** — manifest ยังตั้ง ``"auto_install": False`` เพื่อให้
  operator เลือกติดตั้งเอง deployment ที่ใช้ ``base_assignment`` โดย
  ไม่ต้องการ Todo Inbox ก็ไม่ควรถูกยัด bridge นี้ให้อัตโนมัติ พิจารณาใหม่
  ถ้าอนาคตทุก deployment ใช้ inbox เป็น default อยู่แล้ว
* **Per-consumer todo_category override** — ตอนนี้ tag การแจ้งเตือนของ
  ทุก consumer เป็น ``acknowledgement`` เหมือนกันหมด อนาคตอาจให้ consumer
  เลือก category ของตัวเองได้ (เช่น ``execution`` ถ้า activity มี state
  "done" จริง)

Migration
---------

โมดูลนี้ถูก rename จาก ``procurement_assignment_todo`` (เคยอยู่ในสมัยที่
ยังไม่มี ``base_assignment``) pre-migration ที่
``migrations/16.0.2.0.0/`` rewrite ชื่อ module + ``ir.model.data`` rows
in-place installations เดิม upgrade ต่อได้เลยไม่ต้อง uninstall/reinstall
shim นี้จะเก็บไว้ระยะยาวสำหรับ database ที่ upgrade ช้า

Credits
=======

Authors / ผู้พัฒนา
------------------

* Aginix Technologies
* KMITL (สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง)

Referenced work / งานที่อ้างอิง
--------------------------------

* ``base_assignment`` — mixin หลักที่ bridge นี้ tag
* ``mail_activity_todo`` — engine ของ Todo Inbox
