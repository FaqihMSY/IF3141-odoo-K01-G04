from odoo import models, fields, api
from odoo.exceptions import AccessError

class SukhaMrpProduction(models.Model):
    # Meng-inherit model production bawaan Odoo
    _inherit = 'mrp.production'

    # Menambahkan field khusus sesuai kebutuhan operasional Sukha Delights
    nama_kepala_produksi = fields.Many2one(
        'res.users', 
        string='Manajer Produksi', 
        help="Manajer yang bertanggung jawab menyetujui SPK ini."
    )
    
    staf_produksi_id = fields.Many2one(
        'res.users',
        string='Dikerjakan Oleh (Staf)',
        help="Staf kitchen yang mengeksekusi SPK."
    )
    
    catatan_produksi = fields.Text(
        string='Catatan Tambahan',
        help="Instruksi khusus, misalnya terkait tingkat kematangan croissant atau substitusi bahan."
    )

    def action_confirm(self):
        for record in self:

            if not record.nama_kepala_produksi:

                # Mencegah SPK diselesaikan jika manajer produksi belum diisi
                raise models.ValidationError("Harap isi nama 'Manajer Produksi' sebelum menyelesaikan SPK ini.")
            
            if not record.staf_produksi_id:
                
                # Mencegah SPK diselesaikan jika staf pelaksana belum diisi
                raise models.ValidationError("Harap isi nama 'Staf Produksi' sebelum menyelesaikan SPK ini.")
            

        # Memanggil fungsi asli bawaan Odoo agar stok tetap terpotong secara otomatis
        res = super(SukhaMrpProduction, self).action_confirm()
        return res
    
    def button_mark_done(self):
        for record in self:
            if record.components_availability == 'Not Available' or not record.components_availability:
                
                # Mencegah SPK diselesaikan jika bahan baku tidak mencukupi
                raise models.ValidationError("Tidak dapat menyelesaikan SPK ini karena bahan baku tidak mencukupi.")
        return super(SukhaMrpProduction, self).button_mark_done()