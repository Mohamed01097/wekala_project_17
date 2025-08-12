# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import models, fields, api
from datetime import date

class CustomerCodes(models.Model):
    _name = 'customer.codes'
    _rec_name = 'code'

    partner_id = fields.Many2one('res.partner', string="Customer",domain=lambda self: [('is_company', '=', False)])
    code = fields.Char()
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code already exists for another customer!'),
    ]
class FarmerCodes(models.Model):
    _name = 'farmer.codes'
    _rec_name = 'code'

    partner_id = fields.Many2one('res.partner', string="Farmer",domain=lambda self: [('is_company', '=', True)])
    code = fields.Char()
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code already exists for another farmer!'),
    ]
class ProductCode(models.Model):
    _name = 'product.code'
    _rec_name = 'code'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    code = fields.Char()
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code already exists for another product!'),
    ]
class DailyJournalAgency(models.Model):
    _name = 'daily.journal.agency'
    _description = 'daily.journal.agency'
    _rec_name = 'date'
    _order = 'index'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    index = fields.Integer(
        compute='_compute_line_index'
    )

    def _compute_line_index(self):
        records = self.search([], order='date asc')  # or whatever order you want
        for idx, rec in enumerate(records, start=1):
            rec.index = idx

    customer_code = fields.Many2one('customer.codes', string="Customer Code",required=True)
    customer_id = fields.Many2one(
        'res.partner',
        string="Customer",
        required=True,
        related='customer_code.partner_id',
    )
    farmer_code = fields.Many2one('farmer.codes', string="Farmer Code",required=True)
    farmer = fields.Many2one(
        'res.partner',
        string="Farmer",
        required=True,
        related='farmer_code.partner_id',
    )

    purchase_order = fields.Char(string="Purchase Order" ,readonly=True)

    sale_order = fields.Char( string="Sale Order",readonly=True)

    product_code = fields.Many2one('product.code', string="Product Code",required=True)
    product_id = fields.Many2one('product.product', related='product_code.product_id', string="Product", required=True)
    box_type = fields.Many2one('product.product', string="Box Type", required=True,domain=[('categ_id.is_service', '=', True)])
    box_type_qty = fields.Float(string="Box Quantity",default=1)
    commission_value = fields.Integer(string="Commission",related='product_id.categ_id.commission_value')
    price_unit = fields.Float(string="Unit Price")
    quantity = fields.Float(string="Quantity",default=1)
    number_of_boxes = fields.Integer(string="Incoming")
    date = fields.Date(string="Date", default=fields.Date.today)
    is_sale_created=fields.Boolean(default=False)
    is_purchase_created=fields.Boolean(default=False)
    is_delivery_order=fields.Boolean(default=False)
    is_receipt_order=fields.Boolean(default=False)


    def action_create_sale_orders_today(self):
        transaction_lines = self.env['daily.journal.agency'].search([('is_sale_created','=',False)])
        grouped_by_customer = defaultdict(list)
        for line in transaction_lines:
            customer_id = line.customer_id.id
            grouped_by_customer[customer_id].append(line)

        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        for customer_id, lines in grouped_by_customer.items():
            print("customer_id", customer_id)
            print("lines", lines)
            sale_order = SaleOrder.create({
                'partner_id': customer_id,
            })

            for line in lines:
                SaleOrderLine.create({
                    'order_id': sale_order.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'commission_value': line.commission_value
                })
                line.is_sale_created = True
        return True

    def action_create_purchase_orders_today(self):
        transaction_lines = self.env['daily.journal.agency'].search([('is_purchase_created','=',False)])
        grouped_by_customer = defaultdict(list)

        for line in transaction_lines:
            farmer_id = line.farmer.id
            grouped_by_customer[farmer_id].append(line)

        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']

        for customer_id, lines in grouped_by_customer.items():
            purchase_order = PurchaseOrder.create({
                'partner_id': customer_id,
            })

            for line in lines:
                PurchaseOrderLine.create({
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'price_unit': line.price_unit,
                })
                line.is_purchase_created = True

        return True

    def action_create_delivery_today_records(self):
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        transaction_lines = self.env['daily.journal.agency'].search([
            ('is_delivery_order', '=', False),
        ])

        if not transaction_lines:
            return True

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('warehouse_id.company_id', '=', self.env.company.id)
        ], limit=1)

        source_loc = picking_type.default_location_src_id or picking_type.warehouse_id.lot_stock_id
        dest_loc = picking_type.default_location_dest_id or self.env.ref('stock.stock_location_customers')

        grouped_by_customer = defaultdict(list)
        for line in transaction_lines:
            grouped_by_customer[line.customer_id.id].append(line)

        for partner_id, lines in grouped_by_customer.items():
            partner = self.env['res.partner'].browse(partner_id)
            picking = StockPicking.create({
                'partner_id': partner.id,
                'picking_type_id': picking_type.id,
                'location_id': source_loc.id,
                'location_dest_id': dest_loc.id,
                'origin': f"Daily Journal {fields.Date.today()}",
            })
            for line in lines:
                StockMove.create({
                    'name': line.box_type.display_name,
                    'product_id': line.box_type.id,
                    'product_uom_qty': line.box_type_qty,
                    'product_uom': line.box_type.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source_loc.id,
                    'location_dest_id': dest_loc.id,
                })
                line.write({'is_delivery_order': True})
        return True

    def action_create_receipt_today_records(self):

        transaction_lines = self.env['daily.journal.agency'].search([
            ('is_receipt_order', '=', False),
        ])

        if not transaction_lines:
            return True

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.company_id', '=', self.env.company.id)
        ], limit=1)

        source_loc = picking_type.default_location_src_id or self.env.ref('stock.stock_location_suppliers')
        dest_loc = picking_type.default_location_dest_id or picking_type.warehouse_id.lot_stock_id

        grouped_by_farmer = defaultdict(list)
        for line in transaction_lines:
            grouped_by_farmer[line.farmer.id].append(line)

        for farmer_id, lines in grouped_by_farmer.items():
            partner = self.env['res.partner'].browse(farmer_id)
            picking = self.env['stock.picking'].create({
                'partner_id': partner.id,
                'picking_type_id': picking_type.id,
                'location_id': source_loc.id,
                'location_dest_id': dest_loc.id,
                'origin': f"Daily Journal Receipt {fields.Date.today()}",
            })
            for line in lines:
                self.env['stock.move'].create({
                    'name': line.box_type.display_name,
                    'product_id': line.box_type.id,
                    'product_uom_qty': line.box_type_qty,
                    'product_uom': line.box_type.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': source_loc.id,
                    'location_dest_id': dest_loc.id,
                })
                line.write({'is_receipt_order': True})

        return True

    def action_copy_line(self):
        self.copy()

