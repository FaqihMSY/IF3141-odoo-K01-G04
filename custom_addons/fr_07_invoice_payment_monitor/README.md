# FR-07 Invoice Payment Monitor

Modul ini mengimplementasikan FR-07 tanpa mengubah modul bawaan Odoo. Modul menggunakan invoice dan payment standar Odoo, lalu menambahkan wizard pencatatan pembayaran dan riwayat status pembayaran.

## Cakupan FR

- Input: nomor invoice, jumlah pembayaran, tanggal pembayaran, dan metode pembayaran.
- Operasi: sistem membuat payment Odoo, melakukan rekonsiliasi ke invoice, memperbarui status pembayaran, dan menyimpan riwayat pembayaran FR-07.
- Output: status `Belum Lunas`, `Sebagian`, atau `Lunas` tampil pada invoice beserta riwayat transaksi pembayaran.

## Cara Pakai

1. Pastikan invoice customer sudah `Posted`.
2. Buka invoice dari menu Invoicing.
3. Klik tombol `FR-07 Register Payment`, atau buka menu `FR-07 Register Payment`.
4. Isi nomor invoice, jumlah dibayar, tanggal pembayaran, dan metode pembayaran.
5. Klik `Confirm Payment`.

## Catatan Implementasi

- Invoice tetap memakai model standar Odoo `account.move`.
- Payment tetap memakai proses standar Odoo `account.payment.register`.
- Status FR-07 dihitung dari `payment_state` dan residual invoice bawaan Odoo.
- Riwayat FR-07 disimpan pada model custom `fr07.invoice.payment.log`.
