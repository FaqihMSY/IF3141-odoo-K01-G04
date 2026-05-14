# Invoice Payment Monitoring

Modul ini menambahkan pencatatan pembayaran invoice dan pemantauan status pelunasan secara digital tanpa mengubah modul bawaan Odoo. Modul menggunakan invoice dan payment standar Odoo, lalu menambahkan wizard pencatatan pembayaran, status pelunasan invoice, dan riwayat transaksi pembayaran.

## Kesesuaian FR-07

- Tujuan: mempermudah rekonsiliasi keuangan dengan memantau status pelunasan setiap invoice secara digital.
- Input: nomor invoice, jumlah pembayaran, tanggal pembayaran, dan metode pembayaran.
- Operasi: sistem membuat payment Odoo, melakukan rekonsiliasi ke invoice, memperbarui status pembayaran menjadi `Belum Lunas`, `Sebagian`, atau `Lunas`, dan menyimpan riwayat pembayaran.
- Output: status pembayaran invoice terbaru tampil pada modul keuangan beserta riwayat transaksi pembayaran.
- Integrasi: Accounting, Finance, dan ERP Odoo.

## Cara Pakai

1. Pastikan invoice customer sudah `Posted`.
2. Buka invoice dari menu Invoicing.
3. Klik tombol `Register Payment`, atau buka menu `Register Invoice Payment`.
4. Isi nomor invoice, jumlah dibayar, tanggal pembayaran, dan metode pembayaran.
5. Klik `Confirm Payment`.
6. Sistem akan membuat payment, merekonsiliasi pembayaran ke invoice, memperbarui status pelunasan, dan mencatat riwayat pembayaran.
7. Buka tab `Payment Monitoring` pada invoice atau menu `Payment History` untuk melihat status dan riwayat transaksi.

## Catatan Implementasi

- Invoice tetap memakai model standar Odoo `account.move`.
- Payment tetap memakai proses standar Odoo `account.payment.register`.
- Status pelunasan dihitung dari `payment_state` dan residual invoice bawaan Odoo.
- Riwayat pembayaran disimpan pada model custom `invoice.payment.log`.
