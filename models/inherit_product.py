from odoo import api, fields, models, _
from datetime import datetime

class InMrpProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'    
    
    #product
    nama_desain = fields.Char(string='Nama Desain',)
    no_mesin= fields.Float(string='No Mesin/Jarum',)
    berat= fields.Float(string='Berat/Pasang',)
    warna = fields.Char(string='Warna',required=True, default='NA')
    tgl_buat = fields.Date(string='Tanggal Buat',default=fields.Date.context_today,readonly=True,)
    style = fields.Char(string=u'Style',required=True, default='NA')

    gum_stretch_x= fields.Float(string='Gum Stretch x ',)
    gum_stretch_y= fields.Float(string='Gum Stretch y ',)
    leg_gum_stretch_x= fields.Float(string='Leg Gum Stretch x ',)
    leg_gum_stretch_y= fields.Float(string='Leg Gum Stretch y ',)
    leg_stretch_x= fields.Float(string=' Leg Stretch x',)
    leg_stretch_y= fields.Float(string='Leg Stretch y ',)
    foot_stretch_x= fields.Float(string=' Foot Stretch x',)
    foot_stretch_y= fields.Float(string=' Foot Stretch y',)
    foot_gum_stretch_x= fields.Float(string='Foot Gum Stretch x ',)
    foot_gum_stretch_y= fields.Float(string='Foot Gum Stretch y ',)
    hell_stretch_x= fields.Float(string='Hell Stretch x ',)
    hell_stretch_y= fields.Float(string='Hell Stretch y ',)

    gum_relaxed_x= fields.Float(string='Gum Relaxed x ',)
    gum_relaxed_y= fields.Float(string='Gum Relaxed y ',)
    leg_gum_relaxed_x= fields.Float(string='Leg Gum Relaxed x ',)
    leg_gum_relaxed_y= fields.Float(string='Leg Gum Relaxed y ',)
    leg_relaxed_x= fields.Float(string=' Leg Relaxed x',)
    leg_relaxed_y= fields.Float(string='Leg Relaxed y ',)
    foot_relaxed_x= fields.Float(string=' Foot Relaxed x',)
    foot_relaxed_y= fields.Float(string=' Foot Relaxed y',)
    foot_gum_relaxed_x= fields.Float(string='Foot Gum Relaxed x ',)
    foot_gum_relaxed_y= fields.Float(string='Foot Gum Relaxed y ',)
    hell_relaxed_x= fields.Float(string='Hell Relaxed x ',)
    hell_relaxed_y= fields.Float(string='Hell Relaxed y ',)

    #bahan baku    
    kode_benang = fields.Char(string='Kode Benang',)
    no_warna_benang = fields.Char(string='No Warna Benang',)
    warna_benang = fields.Char(string='Warna Benang',)
    jenis_benang = fields.Char(string='Jenis Benang',)

    #---- 
    size = fields.Char(string='Size Steam',required=True, default='NA')
    kategori = fields.Text(string=u'Kategori',)
    # untuk indukan
    type_kk = fields.Selection([('I', 'I'),('S', "S"),('-', "-")],string='Type KK',)