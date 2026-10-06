from odoo import models, fields, tools

class MissRoseKPI(models.Model):
    _name = "miss.rose.kpi"
    _description = "Indicadores Principales de Miss Rose"
    _auto = False

    name = fields.Char("Etiqueta", readonly=True)
    total_sales = fields.Monetary("Ingreso Total ($)", readonly=True)
    total_orders = fields.Integer("Facturas / Pedidos", readonly=True)
    total_customers = fields.Integer("Clientes", readonly=True)
    average_ticket = fields.Monetary("Gasto Promedio ($)", readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)

    forecast_conservative = fields.Monetary("Pronóstico Conservador ($)", readonly=True)
    forecast_expected = fields.Monetary("Pronóstico Esperado ($)", readonly=True)
    forecast_optimistic = fields.Monetary("Pronóstico Optimista ($)", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # 6. Detectar dinámicamente el nombre de la tabla relacional de categorías de contactos
        rel_table = self.env['res.partner']._fields['category_id'].relation
        if not rel_table:
            rel_table = 'res_partner_res_partner_category_rel'

        # Obtener moneda de la compañía base para evitar agrupaciones erróneas en entornos Multi-Compañía
        currency_id = self.env.ref('base.main_company').currency_id.id or 1
        
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW miss_rose_kpi AS (
                SELECT
                    1 AS id,
                    'Miss Rose Analytics' AS name,
                    (SELECT COALESCE(SUM(am.amount_untaxed_signed), 0) FROM account_move am JOIN {rel_table} pcr ON pcr.partner_id = am.partner_id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE am.move_type IN ('out_invoice', 'out_refund') AND am.state = 'posted' AND pc.name::text ILIKE '%MISS ROSE%') AS total_sales,
                    (SELECT COUNT(DISTINCT am.id) FROM account_move am JOIN {rel_table} pcr ON pcr.partner_id = am.partner_id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE am.move_type = 'out_invoice' AND am.state = 'posted' AND pc.name::text ILIKE '%MISS ROSE%') AS total_orders,
                    (SELECT COUNT(DISTINCT am.partner_id) FROM account_move am JOIN {rel_table} pcr ON pcr.partner_id = am.partner_id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE am.move_type = 'out_invoice' AND am.state = 'posted' AND pc.name::text ILIKE '%MISS ROSE%') AS total_customers,
                    (SELECT CASE WHEN COUNT(DISTINCT am.id) > 0 THEN (SELECT COALESCE(SUM(am2.amount_untaxed_signed), 0) FROM account_move am2 JOIN {rel_table} pcr2 ON pcr2.partner_id = am2.partner_id JOIN res_partner_category pc2 ON pc2.id = pcr2.category_id WHERE am2.move_type IN ('out_invoice', 'out_refund') AND am2.state = 'posted' AND pc2.name::text ILIKE '%MISS ROSE%') / COUNT(DISTINCT am.id) ELSE 0 END FROM account_move am JOIN {rel_table} pcr ON pcr.partner_id = am.partner_id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE am.move_type = 'out_invoice' AND am.state = 'posted' AND pc.name::text ILIKE '%MISS ROSE%') AS average_ticket,
                    {currency_id} AS currency_id,
                    (SELECT COALESCE(SUM(p.mr_forecast_conservative), 0) FROM res_partner p JOIN {rel_table} pcr ON pcr.partner_id = p.id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE pc.name::text ILIKE '%MISS ROSE%') AS forecast_conservative,
                    (SELECT COALESCE(SUM(p.mr_forecast_expected), 0) FROM res_partner p JOIN {rel_table} pcr ON pcr.partner_id = p.id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE pc.name::text ILIKE '%MISS ROSE%') AS forecast_expected,
                    (SELECT COALESCE(SUM(p.mr_forecast_optimistic), 0) FROM res_partner p JOIN {rel_table} pcr ON pcr.partner_id = p.id JOIN res_partner_category pc ON pc.id = pcr.category_id WHERE pc.name::text ILIKE '%MISS ROSE%') AS forecast_optimistic
            )
        """)
