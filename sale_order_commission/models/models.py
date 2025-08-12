from odoo import models, fields, api
from odoo.tools import formatLang


class ProductCategory(models.Model):
    _inherit = 'product.category'
    _description = 'product.category'

    commission_value = fields.Integer(string="Commission")
    is_service  = fields.Boolean(string="Is Service",default=False)



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    outgoing = fields.Integer(string="outgoing")
    commission_value = fields.Integer(string="Commission",related='product_id.categ_id.commission_value')
    commission_result = fields.Monetary(string="Result", compute="_compute_result", store=True)

    @api.depends('outgoing', 'commission_value')
    def _compute_result(self):
        for line in self:
            line.commission_result = (line.outgoing or 0.0) * (line.commission_value or 0.0)

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'commission_result')
    def _compute_amount(self):
        for line in self:
            taxes_res = self.env['account.tax'].with_company(line.company_id)._compute_taxes(
                [line._convert_to_tax_base_line_dict()]
            )
            totals = list(taxes_res['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed'] + line.commission_result
            amount_tax = totals['amount_tax']
            amount_total = amount_untaxed + amount_tax

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_total,
            })


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    @api.depends_context('lang')
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'order_line.commission_result',
                 'order_line.product_uom_qty', 'currency_id')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            order.tax_totals['amount_untaxed'] += sum(order_lines.mapped('commission_result'))

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        for order in self:
            invoice = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
            for line in order.order_line:
                invoice_line = invoice.invoice_line_ids.filtered(
                    lambda l: l.sale_line_ids and l.sale_line_ids[0] == line)
                if invoice_line:
                    invoice_line.write({
                        'commission_result': line.commission_result,
                        'commission_value': line.commission_value,
                        'outgoing': line.outgoing,
                        'price_subtotal': line.price_subtotal,
                        'price_total': line.price_total
                    })


        return invoices

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_tax_totals(self):
        """ Computed field used for custom widget's rendering.
            Only set on invoices.
        """
        for move in self:
            if move.is_invoice(include_receipts=True):
                base_lines = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
                base_line_values_list = [line._convert_to_tax_base_line_dict() for line in base_lines]
                sign = move.direction_sign
                if move.id:
                    # The invoice is stored so we can add the early payment discount lines directly to reduce the
                    # tax amount without touching the untaxed amount.
                    base_line_values_list += [
                        {
                            **line._convert_to_tax_base_line_dict(),
                            'handle_price_include': False,
                            'quantity': 1.0,
                            'price_unit': sign * line.amount_currency,
                        }
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'epd')
                    ]

                kwargs = {
                    'base_lines': base_line_values_list,
                    'currency': move.currency_id or move.journal_id.currency_id or move.company_id.currency_id,
                }

                if move.id:
                    kwargs['tax_lines'] = [
                        line._convert_to_tax_line_dict()
                        for line in move.line_ids.filtered(lambda line: line.display_type == 'tax')
                    ]
                else:
                    # In case the invoice isn't yet stored, the early payment discount lines are not there. Then,
                    # we need to simulate them.
                    epd_aggregated_values = {}
                    for base_line in base_lines:
                        if not base_line.epd_needed:
                            continue
                        for grouping_dict, values in base_line.epd_needed.items():
                            epd_values = epd_aggregated_values.setdefault(grouping_dict, {'price_subtotal': 0.0})
                            epd_values['price_subtotal'] += values['price_subtotal']

                    for grouping_dict, values in epd_aggregated_values.items():
                        taxes = None
                        if grouping_dict.get('tax_ids'):
                            taxes = self.env['account.tax'].browse(grouping_dict['tax_ids'][0][2])

                        kwargs['base_lines'].append(self.env['account.tax']._convert_to_tax_base_line_dict(
                            None,
                            partner=move.partner_id,
                            currency=move.currency_id,
                            taxes=taxes,
                            price_unit=values['price_subtotal'],
                            quantity=1.0,
                            account=self.env['account.account'].browse(grouping_dict['account_id']),
                            analytic_distribution=values.get('analytic_distribution'),
                            price_subtotal=values['price_subtotal'],
                            is_refund=move.move_type in ('out_refund', 'in_refund'),
                            handle_price_include=False,
                            extra_context={'_extra_grouping_key_': 'epd'},
                        ))
                move.tax_totals = self.env['account.tax']._prepare_tax_totals(**kwargs)
                move.tax_totals['amount_untaxed'] += sum(move.invoice_line_ids.mapped('commission_result'))

                if move.invoice_cash_rounding_id:
                    rounding_amount = move.invoice_cash_rounding_id.compute_difference(move.currency_id,
                                                                                       move.tax_totals['amount_total'])
                    totals = move.tax_totals
                    totals['display_rounding'] = True
                    if rounding_amount:
                        if move.invoice_cash_rounding_id.strategy == 'add_invoice_line':
                            totals['rounding_amount'] = rounding_amount
                            totals['formatted_rounding_amount'] = formatLang(self.env, totals['rounding_amount'],
                                                                             currency_obj=move.currency_id)
                            totals['amount_total_rounded'] = totals['amount_total'] + rounding_amount
                            totals['formatted_amount_total_rounded'] = formatLang(self.env,
                                                                                  totals['amount_total_rounded'],
                                                                                  currency_obj=move.currency_id)
                        elif move.invoice_cash_rounding_id.strategy == 'biggest_tax':
                            if totals['subtotals_order']:
                                max_tax_group = max((
                                    tax_group
                                    for tax_groups in totals['groups_by_subtotal'].values()
                                    for tax_group in tax_groups
                                ), key=lambda tax_group: tax_group['tax_group_amount'])
                                max_tax_group['tax_group_amount'] += rounding_amount
                                max_tax_group['formatted_tax_group_amount'] = formatLang(self.env, max_tax_group[
                                    'tax_group_amount'], currency_obj=move.currency_id)
                                totals['amount_total'] += rounding_amount
                                totals['formatted_amount_total'] = formatLang(self.env, totals['amount_total'],
                                                                              currency_obj=move.currency_id)
            else:
                # Non-invoice moves don't support that field (because of multicurrency: all lines of the invoice share the same currency)
                move.tax_totals = None

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    outgoing = fields.Integer(string="outgoing")
    commission_value = fields.Monetary(string="Commission")
    commission_result = fields.Monetary(string="Result")