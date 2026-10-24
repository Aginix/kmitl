# KMITL Student

A student of the institute as an Odoo contact: identified by the institute's own
student ID and named the way the institute's student register names them, so the
student can be paid (or billed) like any other partner.

## Language

**Student** (นักศึกษา):
A contact of the นักศึกษา partner type carrying a **Student ID**. One person, one
contact: the same student paid twice is the same contact both times.
_Avoid_: Student partner, Learner.

**Student ID** (รหัสนักศึกษา):
The institute's code for a student (e.g. `65010001`) — unique across contacts and
the key every student lookup matches on first.
_Avoid_: Student number.

**Student catalog** (ทะเบียนนักศึกษา สจล.):
The institute's register of students, read over its API: the source of a student's
official name, faculty and curriculum. It never supplies a bank account or a national
ID — those come from whoever pays the student (see ADR 0001). Connected only where
`partner_student_kmitl_api` is installed; without it, only students already on a
contact are known.
_Avoid_: Student API (the transport, not the register), REG.

**Refresh from the catalog** (ดึงข้อมูลจาก สจล.):
Re-reading a student's name, faculty and curriculum from the **Student catalog** onto
the contact. Never touches the contact's bank accounts or national ID.
_Avoid_: Sync (nothing flows back to the catalog).
