===================================
Disbursement Stations Configuration
===================================

Seats the stations seeded by ``disbursement_work_center`` when the module is
installed. Each station allows and requires its act, opens its editable parts, and
gets the administrator as a member (act, then editable parts):

* **หมวดตรวจ**: ตรวจสอบ; แก้ไขส่วนหัว, แก้ไขรายการ, แก้ไขไฟล์แนบ
* **ผอ.กองคลัง**: อนุมัติ (ผอ.กองคลัง)
* **ผู้รับมอบอำนาจอธิการบดี**: อนุมัติ (ผู้รับมอบอำนาจ)
* **ตั้งหนี้**: สร้างใบตั้งหนี้; แก้ไขมิติการเงิน, แก้ไขรายการ
* **ตรวจจ่าย**: ตรวจจ่าย; แก้ไขรายการ
* **อนุมัติจ่าย**: อนุมัติจ่าย

The configuration is written once, on install. Upgrading the module does not touch
the stations again, so changes made later by an administrator are kept.

Membership narrows and never grants: while the administrator is the only member of a
station, only the administrator can act there. Add the station's people as members.
