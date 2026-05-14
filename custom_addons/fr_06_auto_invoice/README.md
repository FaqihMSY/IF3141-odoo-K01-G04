# FR-06 Automatic Sales Invoice

Modul ini mengimplementasikan FR-06 tanpa mengubah modul bawaan Odoo. Modul melakukan inheritance pada Sales, Inventory, dan Accounting untuk membuat customer invoice otomatis dari sales order yang delivery order-nya sudah selesai.

## Cakupan FR

- Input: sales order pelanggan beserta produk, kuantitas, dan harga satuan.
- Operasi: sistem membuat invoice dari sales order, menghitung total menggunakan engine Accounting Odoo, lalu mem-post invoice agar nomor invoice unik dibuat oleh sequence resmi Odoo.
- Output: invoice digital `account.move` tersimpan di database dan dapat dikirim atau dicetak melalui fitur invoice bawaan Odoo.

## Cara Kerja

1. User membuat dan mengonfirmasi sales order.
2. User memvalidasi delivery order sampai status `Done`.
3. Modul otomatis membuat dan mem-post customer invoice dari sales order tersebut.
4. Cron `FR-06 Auto Invoice Ready Sales Orders` berjalan tiap 10 menit sebagai fallback jika ada order siap invoice yang terlewat.

## Catatan Implementasi

- Modul menggunakan extend/inheritance, bukan modifikasi source bawaan.
- Nomor invoice unik menggunakan sequence standar Odoo saat invoice di-post.
- Field teknis FR-06 ditambahkan pada sales order dan invoice untuk audit hasil auto-generate.
