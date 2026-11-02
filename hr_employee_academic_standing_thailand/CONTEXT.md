# HR Employee Academic Standing Thailand

Adds Thai academic-standing information to employees — the คำนำหน้าชื่อทางวิชาการ
(academic title prefix) built from academic standing, rank, profession, rank nobility
and a ดร. flag.

## Language

**Academic Standing Title (คำนำหน้าชื่อทางวิชาการ)**: The computed prefix string placed
before an employee's name. For an academic-role employee it is assembled from academic
standing, rank, the ดร. flag ("ดร."/"Dr." when set), profession and rank nobility; for a
support-role employee it is job + position level. Stored in four variants: Thai full,
Thai abbreviation, English full, English abbreviation. _Avoid_: prefix, honorific,
salutation

**ดร. flag (`title_dr`)**: A per-employee boolean that decides whether "ดร."/"Dr." is
injected into the academic-role title prefix. Set by hand on the employee form in this
base module; the add-on `hr_employee_academic_standing_thailand_dr_auto` turns it into
an automatic value derived from the employee's highest education level (ปริญญาเอก →
true). _Avoid_: PhD title, doctorate — the flag is a display toggle, not a degree
record.
