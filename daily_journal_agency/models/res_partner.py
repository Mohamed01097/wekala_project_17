from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    box_type_ids = fields.One2many('box.type.product', 'partner_id', string='Box Type')


class BoxTypeProduct(models.Model):
    _name = 'box.type.product'
    _description = 'Box Type Product'

    partner_id = fields.Many2one('res.partner', string='Partner')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float()

    def open_product_history(self):
        return {
            'name': 'Product History',
            'view_mode': 'tree',
            'res_model': 'stock.move.line',
            'domain': [('product_id', '=', self.product_id.id)],
            'type': 'ir.actions.act_window',
        }

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for picking in self:
            for product in picking.move_ids_without_package.mapped('product_id'):
                if not product.categ_id.is_service:
                    continue

                incoming_qty = self.env['stock.move.line'].search([
                    ('picking_id.partner_id', '=', picking.partner_id.id),
                    ('product_id', '=', product.id),
                    ('product_id.categ_id.is_service', '=', True),
                    ('state', '=', 'done'),
                    ('picking_code', '=', 'incoming')
                ]).mapped('quantity')
                incoming_qty_total = sum(incoming_qty)

                outgoing_qty = self.env['stock.move.line'].search([
                    ('picking_id.partner_id', '=', picking.partner_id.id),
                    ('product_id', '=', product.id),
                    ('product_id.categ_id.is_service', '=', True),
                    ('state', '=', 'done'),
                    ('picking_code', '=', 'outgoing')
                ]).mapped('quantity')
                outgoing_qty_total = sum(outgoing_qty)

                balance_qty = outgoing_qty_total- incoming_qty_total

                existing_line = picking.partner_id.box_type_ids.filtered(lambda l: l.product_id == product)
                if existing_line:
                    existing_line.write({'quantity': balance_qty})
                else:
                    self.env['box.type.product'].create({
                        'partner_id': picking.partner_id.id,
                        'product_id': product.id,
                        'quantity': balance_qty
                    })

        return res

