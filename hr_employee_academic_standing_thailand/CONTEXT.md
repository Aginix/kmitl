# HR Employee Academic Standing Thailand

Adds Thai academic-standing information to employees — the คำนำหน้าชื่อทางวิชาการ
(academic title prefix) built from academic standing, rank, profession, rank nobility
and education level.

## Language

**Academic Standing Title (คำนำหน้าชื่อทางวิชาการ)**: The computed prefix string placed
before an employee's name. For an academic-role employee it is assembled from academic
standing, rank, "ดร."/"Dr." (when the education level is a PhD), profession and rank
nobility; for a support-role employee it is job + position level. Stored in four
variants: Thai full, Thai abbreviation, English full, English abbreviation. _Avoid_:
prefix, honorific, salutation
