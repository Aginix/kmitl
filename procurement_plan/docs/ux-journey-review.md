# รีวิว UX: user journey แผนจัดซื้อจัดจ้าง (2569-11-07)

ที่มาของรีวิว: ผู้ใช้แจ้งว่า "เมื่อกดปุ่มเปลี่ยนสถานะจากแบบร่างแล้ว กลับเป็นแบบร่างไม่ได้ และแก้ตัวเลขอะไรไม่ได้เลย"

ทดสอบบนสำเนาของ `snapshot-20261107` ซึ่งเป็นข้อมูล production วันที่ 7 พ.ย. ใช้โค้ด branch นี้ และรุ่นโมดูลตรงกับ prod ขับหน้าจอด้วย Playwright ใน 2 บทบาท:

- **ผู้ใช้แผน:** user 2118 คณะอุตสาหกรรมอาหาร มีสิทธิ์ `group_procurement_plan_user` และ `budget.group_budget_user`
- **ผู้จัดการแผน:** user 3107 สำนักงานอธิการบดี (`role_planning_officer_admin`)

ภาพหน้าจออยู่ใน `.context/ux-review/` (gitignored เพราะมีข้อมูลจริง) ส่วนสคริปต์ steps ที่ใช้ทดสอบซ้ำอยู่ในโฟลเดอร์เดียวกัน

## 1. ข้อมูลจริงยืนยันปัญหา

| ที่มา | draft | to_verify | verified | in_progress | cancel |
|---|---|---|---|---|---|
| สร้างจากประมาณการรายจ่าย | 1 | 0 | 85 | 10 | 0 |
| สร้างเอง | 0 | **19** | 6 | 1 | 4 |

- แผนที่สร้างเอง **19 จาก 30 ค้างอยู่ที่ `to_verify`** สร้างระหว่าง 7–29 ต.ค.
- **ทั้ง 19 แผนยังไม่ได้รับเงิน** (`budget_amount = 0`), ไม่มี Held Money และไม่มีใบจอง
- ผลคือการให้แผนเหล่านี้กลับไปแก้ไขไม่กระทบเงินเลย
- แผนที่เกิดจากประมาณการรายจ่ายข้ามไป `verified` ทันที จึงไม่เจอปัญหานี้ ตรงกับที่ผู้ใช้ตั้งข้อสังเกตไว้

## 2. Journey ที่พบจริง

### Journey A: สร้างเอง

```
แบบร่าง ──[ส่งเข้ารอจัดสรรงบประมาณ]──▶ รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ
   (ไม่มี confirm)                       │  งานแผนโอนงบเข้า / จัดสรรงบลอย
                                         ▼
                                    [จองงบประมาณ] ──▶ รอดำเนินการ ──[สร้างใบขอซื้อ]──▶ อยู่ในระหว่างดำเนินการ ──[ปิดแผน]──▶ เสร็จสิ้น
```

### Journey B: จากประมาณการรายจ่าย

ระบบ post appropriation แล้วแผนข้าม draft → to_verify → verified ให้อัตโนมัติ ผู้ใช้เห็นแผนครั้งแรกตอนเป็น "รอดำเนินการ" แล้ว ซึ่งไม่มีปัญหา

### Matrix: ฟิลด์ที่แก้ได้ (rw) ตามที่ Playwright เห็นจริง

| ฟิลด์ | draft | to_verify | verified | in_progress |
|---|---|---|---|---|
| ชื่อรายการ `description` | rw | rw | rw | rw |
| จำนวน / หน่วย `amount/unit` | rw | **RO** | RO | RO |
| วงเงินรวม `total_price` | rw | **RO** | RO | RO |
| ผู้ใช้ `user_id` | rw | RO | RO | RO |
| โน้ต, ผู้รับผิดชอบ, เอกสารแนบ | rw | rw | rw | rw |
| ปีงบ / มิติ 4 ตัว / รหัสงบ | rw | RO | RO | RO |
| ETA 5 ช่อง / วิธีจัดซื้อ | rw | rw | rw | **RO** |
| งวดงาน `payment_ids` | rw | rw | rw | rw (ไม่ล็อกเลย) |

### Matrix: ปุ่มบน header

| สถานะ | ผู้ใช้แผน | ผู้จัดการแผน |
|---|---|---|
| draft | ส่งเข้ารอจัดสรรงบประมาณ | (เหมือนกัน) |
| to_verify | จองงบประมาณ, จัดสรรงบประมาณ (งบลอย) | + **RESET TO DRAFT** |
| verified | สร้างใบขอซื้อ, จัดสรรงบลอย, โอนคืนงบลอย | (เหมือนกัน) |
| in_progress | — | ปิดแผน, สร้างใบขอซื้อ, จัดสรรงบลอย, โอนคืนงบลอย |

## 3. Pain points

| # | ความรุนแรง | ปัญหา | หลักฐาน |
|---|---|---|---|
| 1 | **สูง** | ผู้ใช้แผน**ไม่มีทางกลับเป็นแบบร่าง** ปุ่ม Reset ให้เห็นและใช้ได้เฉพาะผู้จัดการแผน (ADR-0002) ผู้ใช้ทั่วไปจึงต้องไปขอผู้จัดการแผนส่วนกลางให้กดให้ | `A2-to_verify.png` vs `M1`; `procurement_plan.py:406` `_check_plan_manager` |
| 2 | **สูง** | ที่ `to_verify` **แก้จำนวน/หน่วย/วงเงินรวมไม่ได้** ทั้งที่ยังไม่ได้รับเงินและยังไม่จองงบ | matrix ด้านบน; `can_edit` เป็น True เฉพาะ draft (`procurement_plan.py:438`) และ `READONLY_STATES` (`:34`) |
| 3 | **สูง** | ปุ่ม "ส่งเข้ารอจัดสรรงบประมาณ" **ไม่มี confirm** และไม่มีคำเตือนว่ากดแล้วจะถูกล็อก | `confirm dialog after send: 0`; `procurement_plan_views.xml:33` |
| 4 | กลาง | ปุ่ม **"จองงบประมาณ" เป็น primary ทั้งที่ยังไม่ได้รับเงิน** กดแล้วได้ error ทันที ซึ่งเป็นปุ่มที่ไม่ควรกดในสถานะนี้ อีกทั้งไม่มี `groups` ทั้งที่ ADR-0002 ระบุว่าจองงบเป็นสิทธิ์ budget user | `M2-verify-error.png`; `procurement_plan_views.xml:34` |
| 5 | กลาง | กติกาการล็อกกระจายอยู่ 4 ชั้น ได้แก่ `READONLY_STATES` ใน model, `can_edit`, `can_edit_description` และ attrs ราย field (ETA ใช้ state list ของตัวเอง) ผลคือไม่สอดคล้องกัน เช่น `total_price` ล็อกเฉพาะใน view, `payment_ids` ไม่ล็อกแม้ in_progress และ `description` มี `states` readonly แต่ attrs กลับเปิดให้แก้ | `procurement_plan.py:34–170`, view `:58–96` |
| 6 | กลาง | label สถานะ to_verify ยาวเกิน **"รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจองงบประมาณ"** badge ใน list ถูกตัดเป็น "รอจัดสรรงบประมาณ (ปรับเข้าแผน) และจ..." และ filter ใน search ใช้ชื่ออื่น ("จัดสรรงบประมาณ (ปรับเข้าแผน)") | `M0-list-filters.png`; `procurement_plan_budget/models/procurement_plan.py:20`; search view `:157` |
| 7 | กลาง | ไม่บอกว่า**ขั้นถัดไปคืออะไรและใครต้องทำ** ใน draft ไม่มีคำอธิบาย ส่วนใน to_verify มีแบนเนอร์ "รองานแผนโอนงบ" แต่ไม่บอกว่าถ้าต้องแก้ข้อมูลต้องทำอย่างไร | `A1-draft.png`, `A2-to_verify.png` |
| 8 | ต่ำ | label ภาษาอังกฤษปน: "RESET TO DRAFT", แท็บ "Additional Info", stat "Budget ..." ถูกตัด และ Todo "Complete the operating plan (ETAs + procurement method)…" | `A2-to_verify.png`; `procurement_plan_todo/data/mail_activity_type.xml:5` |
| 9 | ต่ำ | Reset to Draft ไม่มี confirm ทั้งที่ใน `verified` จะยกเลิกใบจองไปด้วย | `reset confirm dialog: 0` |
| 10 | ต่ำ | เมนูเกียร์มี **"เก็บถาวร"** ซึ่งเป็นการ archive ตรงๆ ข้ามกติกาลบแผนใน ADR-0005 (`_check_deletable`) | gear menu: `["เก็บถาวร","ทำซ้ำ","ลบ"]` |
| 11 | ต่ำ | หลัง Reset แล้ว **ปีงบประมาณยังล็อก** เพราะ attrs ผูกกับ `analytic_account_id` ซึ่งยังอยู่ | `M3-after-reset` fields `account_fiscal_year_id:RO` |
| 12 | ต่ำ | มีแผนจากประมาณการรายจ่ายค้างเป็น draft อยู่ 1 แผน (30 ก.ย.) น่าจะเป็นข้อมูลค้างจากการ post ที่ไม่สำเร็จ ควรตรวจแยก | SQL ในข้อ 1 |

## 4. ข้อเสนอแก้

### P1: แก้ feedback โดยตรง (procurement_plan, procurement_plan_budget)

**P1-a ✅ ตัดสินแล้ว: ฟิลด์ข้อมูลแผนแก้ได้ตลอด**
- `description`, `amount`, `unit`, `total_price`, `note` แก้ได้ทุกสถานะยกเว้น `done` และ `cancel`
- `payment_ids` (งวดงาน) แก้ได้ถึง `to_verify`
- มิติ 4 ตัว, รหัสงบ, ปีงบ และ `user_id` ยังล็อกหลังส่ง
- วิธีทำ:
  - เอา `states=READONLY_STATES` ออกจาก 4 ฟิลด์แรก
  - แยก compute เป็น `can_edit_details` (state ไม่อยู่ใน done/cancel) กับ `can_edit` (= draft, ใช้กับมิติ) ส่วน `can_edit_description` ยุบรวมเข้า `can_edit_details`
  - ปรับ attrs ใน view ของ `procurement_plan` และ `procurement_plan_budget`
- ความเสี่ยงด้านเงินต่ำ:
  - การจองงบใช้ `budget_amount` ไม่ใช่ `total_price` (ADR-0003)
  - ถ้า `total_price` สูงกว่างบที่ได้รับ แบนเนอร์ `budget_short` จะเตือนเอง และ `_reserve_plan_commitment` จะไม่ยอมจอง
  - การแก้ `description` sync ไปที่ analytic อยู่แล้ว (`write`)
- ขนาดงาน: S

**P1-b ❓ ให้ตัดสิน: ผู้ใช้แผนกด "ดึงกลับเป็นแบบร่าง" ได้เอง**
- เงื่อนไข: เฉพาะ `to_verify` ที่ไม่มี Held Money และไม่มีใบจอง ซึ่งข้อมูลจริงตรงเงื่อนไขทั้ง 19 แผน
- ใช้เมื่อต้องแก้มิติหรือรหัสงบ
- Reset จาก `verified` และ `cancel` ยังเป็นสิทธิ์ผู้จัดการแผน
- ต้องแก้ ADR-0002 ในข้อ "Reset = plan manager" โดยเพิ่ม amendment
- วิธีทำ: ปุ่มที่ 2 สำหรับ `group_procurement_plan_user` ซึ่งเรียก `action_reset_to_draft` และ `_check_plan_manager` ยอมผ่านเมื่อ `state == 'to_verify' and not has_held_money`
- ขนาดงาน: S

**P1-c: confirm บนปุ่มส่ง และแบนเนอร์ "ขั้นถัดไป"**
- confirm: "ส่งแผนเข้ารอจัดสรรงบประมาณ? ระบบจะออกเลขที่แผน หลังส่งแล้วแก้มิติ/รหัสงบไม่ได้"
- แบนเนอร์ใน draft: บอกให้กรอกข้อมูลให้ครบแล้วกดส่ง
- แบนเนอร์ใน to_verify: เพิ่มบรรทัด "ต้องแก้มิติ/รหัสงบ → กดดึงกลับเป็นแบบร่าง (หรือติดต่อผู้จัดการแผน)"
- ขนาดงาน: XS

### P2: ลดความสับสน

- **P2-a:** ปุ่ม "จองงบประมาณ"
  - ซ่อนเมื่อ `budget_amount = 0` หรือ `budget_short` เป็นจริง
  - ใส่ `groups="budget.group_budget_user"` ให้ตรงกับ ADR-0002
  - เปลี่ยนจาก primary เป็นปุ่มปกติตอนที่ยังจองไม่ได้ (pain #4)
- **P2-b:** label สถานะ to_verify ให้สั้นลง เช่น **"รอจัดสรรงบประมาณ"** (portal ใช้คำนี้อยู่แล้ว `procurement_plan_portal/controllers/main.py:20`) และให้ชื่อ filter ใน search ตรงกัน (pain #6)
- **P2-c:** เปลี่ยน "Reset to Draft" เป็น "กลับเป็นแบบร่าง" พร้อม confirm (โดยเฉพาะใน verified ที่ใบจองจะถูกยกเลิก) (pain #8, #9)
- **P2-d:** ย้ายกติกา readonly มารวมไว้ที่ compute ชุดเดียว และให้ `payment_ids` ล็อกตั้งแต่ in_progress (pain #5) ส่วนนี้ทำพร้อม P1-a ได้

### P3: เก็บงาน

- แปลข้อความ Todo, แท็บ "Additional Info" และ stat "Budget …" (pain #8)
- ซ่อน "เก็บถาวร" ออกจากเมนูเกียร์ หรือ override `action_archive` ให้ผ่าน `_check_deletable` (pain #10)
- ปลดล็อกปีงบหลัง Reset ด้วย attrs ผูกกับ `state` แทน `analytic_account_id` (pain #11) ต้องระวังเรื่องเลขที่แผนซึ่งออกตามปีงบไปแล้ว
- ตรวจแผน draft ที่ค้างจาก appropriation (pain #12)

## 5. ผลกระทบด้าน deploy

- procurement_plan family อยู่ใน production แล้ว ทุกข้อที่แตะ view/data ต้อง bump version:
  - `procurement_plan` (P1-a/b/c, P2-c/d)
  - `procurement_plan_budget` (P1-a, P2-a/b)
  - `procurement_plan_todo` (P3)
- ไม่มี migration ข้อมูล เพราะเป็นการเปลี่ยนเฉพาะ readonly, ปุ่ม และ label
- ต้องปรับเอกสาร:
  - ADR-0002 (ถ้าเลือก P1-b)
  - `CONTEXT.md` ในหัวข้อ **Submit** ("the single act that takes a plan out of drafting") และ **Preparer** ("fixed once submitted") ให้ตรงกับกติกาการแก้ไขใหม่

## 6. สิ่งที่รีวิวนี้ไม่ได้ครอบคลุม

- portal สาธารณะ (ไม่ได้ติดตั้งใน prod snapshot) และหน้า บัญชีแผน (`procurement_plan_budget_overview` ก็ยังไม่ได้ติดตั้งใน prod)
- ขั้นจัดสรรงบลอยไปจนถึงการสร้างใบขอซื้อ ซึ่งไม่ได้กดจริง ดูเพียงปุ่มที่แสดงในแต่ละสถานะ
- ผู้ใช้แผนที่**ไม่มี** budget user เพราะ user ที่ทดสอบมีสิทธิ์นี้ด้วย
