Adds **รหัสงบประมาณ** (`budget_account_id`) to the payment voucher
(`account.payment`): on the voucher form's dimensions tab and as the first row
of the printed ใบสำคัญจ่าย's dimensions table.

A source module opts its vouchers in by overriding
`_compute_is_budget_code_required`. An opted-in voucher shows the field as
required, and ยืนยันส่งธนาคาร refuses it while ส่วนงาน, แหล่งเงิน, กองทุน,
ด้าน/แผนงาน/กิจกรรม or the รหัสงบประมาณ is missing. Other vouchers are unchanged.
