# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta

class ResPartner(models.Model):
    _inherit = 'res.partner'

    mr_currency_id = fields.Many2one(
        'res.currency', 
        string="Moneda (Miss Rose)", 
        compute='_compute_mr_currency_id'
    )

    @api.depends('company_id')
    def _compute_mr_currency_id(self):
        default_currency = self.env.company.currency_id
        for partner in self:
            partner.mr_currency_id = partner.company_id.currency_id or default_currency


    mr_last_purchase_date = fields.Date(string="Última Fecha de Compra", compute="_compute_mr_purchase_stats", store=True)
    mr_last_purchase_amount = fields.Monetary(string="Monto Última Compra", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_total_purchase = fields.Monetary(string="Total Comprado", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_purchase_count = fields.Integer(string="Cantidad de Compras", compute="_compute_mr_purchase_stats", store=True)
    mr_average_ticket = fields.Monetary(string="Ticket Promedio", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_monthly_forecast = fields.Monetary(string="Pronóstico Mensual", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_forecast_probability = fields.Float(string="Probabilidad (%)", compute="_compute_mr_purchase_stats", store=True)
    mr_days_since_purchase = fields.Integer(string="Días desde Última Compra", compute="_compute_mr_purchase_stats", search="_search_mr_days_since_purchase", store=True)
    mr_next_purchase_prob = fields.Date(string="Probabilidad Próxima Compra", compute="_compute_mr_purchase_stats", store=True)
    mr_forecast_confidence = fields.Selection([('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja')], string="Confianza", compute="_compute_mr_purchase_stats", store=True)
    mr_expected_ticket = fields.Monetary(string="Ticket Esperado", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_avg_days_between = fields.Float(string="Frecuencia Habitual (Días)", compute="_compute_mr_purchase_stats", store=True)
    mr_forecast_conservative = fields.Monetary(string="Pronóstico Conservador", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_forecast_expected = fields.Monetary(string="Pronóstico Esperado", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    mr_forecast_optimistic = fields.Monetary(string="Pronóstico Optimista", compute="_compute_mr_purchase_stats", currency_field='mr_currency_id', store=True)
    
    # Campo para relacionar de forma segura las facturas de Odoo sin depender ciegamente de la estructura de la base
    mr_invoice_ids = fields.One2many('account.move', 'partner_id', string="Facturas y Reembolsos", domain=[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')])

    mr_birthday_day = fields.Integer(string="Día de Cumpleaños")
    mr_birthday_month = fields.Selection([
        ('01', 'Enero'),
        ('02', 'Febrero'),
        ('03', 'Marzo'),
        ('04', 'Abril'),
        ('05', 'Mayo'),
        ('06', 'Junio'),
        ('07', 'Julio'),
        ('08', 'Agosto'),
        ('09', 'Septiembre'),
        ('10', 'Octubre'),
        ('11', 'Noviembre'),
        ('12', 'Diciembre'),
    ], string="Mes de Cumpleaños")
    mr_birthday_display = fields.Char(string="Día y Mes", compute="_compute_mr_birthday_display")
    is_birthday_today = fields.Boolean(string="Cumpleaños Hoy", compute="_compute_is_birthday_today", search="_search_is_birthday_today")
    
    mr_maps_url = fields.Char(string="Dirección Maps del Cliente")

    @api.depends('mr_birthday_day', 'mr_birthday_month')
    def _compute_is_birthday_today(self):
        today = fields.Date.today()
        for partner in self:
            if partner.mr_birthday_day and partner.mr_birthday_month:
                partner.is_birthday_today = (partner.mr_birthday_day == today.day and int(partner.mr_birthday_month) == today.month)
            else:
                partner.is_birthday_today = False

    def _search_is_birthday_today(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return []
            
        today = fields.Date.today()
        self.env.cr.execute("""
            SELECT id 
            FROM res_partner 
            WHERE mr_birthday_month = %s 
              AND mr_birthday_day = %s
        """, (str(today.month).zfill(2), today.day))
        
        ids = [r[0] for r in self.env.cr.fetchall()]
        
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', ids)]
        else:
            return [('id', 'not in', ids)]

    @api.depends('mr_birthday_day', 'mr_birthday_month')
    def _compute_mr_birthday_display(self):
        months = dict(self._fields['mr_birthday_month'].selection)
        for partner in self:
            if partner.mr_birthday_day and partner.mr_birthday_month:
                partner.mr_birthday_display = f"{partner.mr_birthday_day} de {months.get(partner.mr_birthday_month)}"
            else:
                partner.mr_birthday_display = ""

    @api.depends('mr_invoice_ids', 'mr_invoice_ids.state', 'mr_invoice_ids.move_type', 'mr_invoice_ids.invoice_date', 'mr_invoice_ids.amount_untaxed_signed')
    def _compute_mr_purchase_stats(self):
        import math
        
        # PREVENCIÓN N+1: Buscar todas las facturas de una sola vez
        commercial_ids = self.mapped('commercial_partner_id').ids
        if commercial_ids:
            all_invoices = self.env['account.move'].search([
                ('commercial_partner_id', 'in', commercial_ids),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
            ], order='invoice_date desc')
        else:
            all_invoices = []
            
        invoices_by_partner = {}
        for inv in all_invoices:
            pid = inv.commercial_partner_id.id
            if pid not in invoices_by_partner:
                invoices_by_partner[pid] = []
            invoices_by_partner[pid].append(inv)
            
        for partner in self:
            invoices = invoices_by_partner.get(partner.commercial_partner_id.id, [])
            sales_invoices = [inv for inv in invoices if inv.move_type == 'out_invoice']

            if not sales_invoices:
                partner.mr_last_purchase_date = False
                partner.mr_last_purchase_amount = 0.0
                partner.mr_total_purchase = 0.0
                partner.mr_average_ticket = 0.0
                partner.mr_purchase_count = 0
                partner.mr_days_since_purchase = 0
                partner.mr_next_purchase_prob = False
                partner.mr_monthly_forecast = 0.0
                partner.mr_forecast_probability = 0.0
                partner.mr_forecast_confidence = 'baja'
                partner.mr_expected_ticket = 0.0
                partner.mr_avg_days_between = 0.0
                partner.mr_forecast_conservative = 0.0
                partner.mr_forecast_expected = 0.0
                partner.mr_forecast_optimistic = 0.0
                continue

            # Estadísticas Básicas (Ventas netas incluyen devoluciones, la frecuencia solo ventas reales)
            partner.mr_last_purchase_date = sales_invoices[0].invoice_date
            partner.mr_last_purchase_amount = sales_invoices[0].amount_untaxed_signed
            partner.mr_total_purchase = sum(inv.amount_untaxed_signed for inv in invoices)
            partner.mr_purchase_count = len(sales_invoices)
            partner.mr_average_ticket = partner.mr_total_purchase / partner.mr_purchase_count if partner.mr_purchase_count else 0.0

            if partner.mr_last_purchase_date:
                delta = fields.Date.today() - partner.mr_last_purchase_date
                partner.mr_days_since_purchase = delta.days
            else:
                partner.mr_days_since_purchase = 0

            # Cálculos Avanzados (Frecuencia y Regularidad)
            days_diffs = []
            if len(sales_invoices) > 1:
                # Invoices are ordered by date desc
                for i in range(len(sales_invoices) - 1):
                    if sales_invoices[i].invoice_date and sales_invoices[i+1].invoice_date:
                        diff = (sales_invoices[i].invoice_date - sales_invoices[i+1].invoice_date).days
                        days_diffs.append(abs(diff))
            
            avg_days = 0.0
            stdev = 0.0
            if days_diffs:
                avg_days = sum(days_diffs) / len(days_diffs)
                if len(days_diffs) > 1:
                    variance = sum((x - avg_days) ** 2 for x in days_diffs) / (len(days_diffs) - 1)
                    stdev = math.sqrt(variance)

            partner.mr_avg_days_between = avg_days
            if avg_days > 0 and partner.mr_last_purchase_date:
                partner.mr_next_purchase_prob = partner.mr_last_purchase_date + timedelta(days=int(avg_days))
            else:
                partner.mr_next_purchase_prob = False

            # Ticket Esperado (Media Móvil Ponderada: peso mayor a las recientes)
            expected_ticket = 0.0
            if len(sales_invoices) > 0:
                total_weight = 0
                weighted_sum = 0
                # Tomar hasta las ultimas 10 compras para el modelo ponderado
                recent_invoices = sales_invoices[:10]
                n = len(recent_invoices)
                for i, inv in enumerate(recent_invoices):
                    weight = n - i # la más reciente tiene peso n, la más antigua peso 1
                    weighted_sum += inv.amount_untaxed_signed * weight
                    total_weight += weight
                expected_ticket = weighted_sum / total_weight if total_weight > 0 else partner.mr_average_ticket
            
            partner.mr_expected_ticket = expected_ticket

            # Cálculo de Probabilidad (Modelo de Decaimiento)
            days_since = partner.mr_days_since_purchase
            prob = 0.0
            
            if avg_days == 0:
                # Comprador de una sola vez
                if days_since <= 30:
                    prob = 0.50
                elif days_since <= 90:
                    prob = 0.10
                else:
                    prob = 0.02
            else:
                # Calcular días hasta la próxima compra esperada
                days_until_next = avg_days - days_since
                
                if days_until_next > 30:
                    # Falta mucho para que vuelva a comprar
                    prob = 0.05
                elif days_until_next >= 0:
                    # Se espera que compre en los próximos 30 días
                    # A menor desviación estándar (más regular), más alta la probabilidad
                    base_prob = 0.85
                    if stdev < (avg_days * 0.3):
                        base_prob = 0.95
                    prob = base_prob
                else:
                    # Está atrasado (Overdue)
                    days_overdue = -days_until_next
                    cycles_missed = days_overdue / avg_days
                    
                    if cycles_missed <= 1:
                        # Un poco atrasado, penalización leve (Decay)
                        prob = 0.85 - (cycles_missed * 0.35) # de 85% a 50%
                    else:
                        # Muy atrasado, posible churn
                        prob = max(0.01, 0.50 - ((cycles_missed - 1) * 0.15))

            partner.mr_forecast_probability = prob

            # Confianza
            if len(sales_invoices) >= 5 and (avg_days > 0 and stdev < (avg_days * 0.5)):
                partner.mr_forecast_confidence = 'alta'
            elif len(sales_invoices) >= 3:
                partner.mr_forecast_confidence = 'media'
            else:
                partner.mr_forecast_confidence = 'baja'

            # Pronósticos Globales
            expected = expected_ticket * prob
            
            # Si compra varias veces al mes, multiplicamos el ticket esperado
            if avg_days > 0 and avg_days < 30:
                purchases_per_month = 30.0 / avg_days
                expected = expected * purchases_per_month
                
            partner.mr_forecast_expected = expected
            partner.mr_monthly_forecast = expected
            partner.mr_forecast_optimistic = expected_ticket * min(prob * 1.2, 1.0) * (30.0/avg_days if 0 < avg_days < 30 else 1)
            partner.mr_forecast_conservative = expected * 0.8

    def _search_mr_days_since_purchase(self, operator, value):
        target_date = fields.Date.today() - timedelta(days=value)
        self.env.cr.execute("""
            SELECT commercial_partner_id, MAX(invoice_date) as last_date
            FROM account_move
            WHERE move_type = 'out_invoice' AND state = 'posted' AND commercial_partner_id IS NOT NULL
            GROUP BY commercial_partner_id
        """)
        results = self.env.cr.dictfetchall()
        
        matched_partner_ids = []
        for row in results:
            last_date = row['last_date']
            if not last_date: continue
            
            if operator == '<=' and last_date >= target_date:
                matched_partner_ids.append(row['commercial_partner_id'])
            elif operator == '>' and last_date < target_date:
                matched_partner_ids.append(row['commercial_partner_id'])
                
        if operator == '>' and value >= 90:
            self.env.cr.execute("""
                SELECT id FROM res_partner 
                WHERE id NOT IN (
                    SELECT DISTINCT commercial_partner_id FROM account_move WHERE move_type = 'out_invoice' AND state = 'posted' AND commercial_partner_id IS NOT NULL
                )
            """)
            matched_partner_ids.extend([r[0] for r in self.env.cr.fetchall()])
            
        return [('id', 'in', matched_partner_ids)]

    def action_view_mr_invoices(self):
        self.ensure_one()
        return {
            'name': f'Facturas y Devoluciones de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('partner_id', 'child_of', self.id), ('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')],
            'context': {'default_partner_id': self.id, 'default_move_type': 'out_invoice', 'create': False, 'edit': False, 'delete': False},
        }

    @api.model
    def _cron_update_miss_rose_stats(self):
        """Cron job to force recompute of time-sensitive fields for Miss Rose partners."""
        partners = self.search([('category_id.name', 'ilike', 'MISS ROSE')])
        # Call the compute method manually so the stored fields are updated in the database
        partners._compute_mr_purchase_stats()

    def action_send_whatsapp_birthday(self):
        self.ensure_one()
        if not self.mobile and not self.phone:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'El cliente no tiene un número de celular registrado.',
                    'type': 'danger',
                    'sticky': False,
                }
            }
        
        phone = self.mobile or self.phone
        phone_formatted = ''.join(c for c in phone if c.isdigit())
        
        if len(phone_formatted) == 8:
            phone_formatted = '503' + phone_formatted
            
        import urllib.parse
        message = (
            f"¡Hola, {self.name}!\n\n"
            f"Hoy es una fecha verdaderamente especial, y en nombre de toda la familia de Miss Rose no queríamos dejar pasar la oportunidad de felicitarte en este gran día. "
            f"¡Todo nuestro equipo te desea un MUY FELIZ CUMPLEAÑOS!\n\n"
            f"Esperamos de todo corazón que pases un día extraordinario rodeado de tus seres queridos, lleno de alegría, agradables sorpresas y momentos inolvidables. "
            f"Que este nuevo año de vida venga cargado de muchísima salud, prosperidad, grandes éxitos y toda la energía para que sigas cumpliendo cada una de tus metas.\n\n"
            f"Para nosotros es un honor contar con tu preferencia y nos llena de alegría que seas parte de nuestra familia. Siempre estaremos aquí para ofrecerte lo mejor.\n\n"
            f"¡Disfruta al máximo tu celebración y que sean muchísimos años más! Un abrazo enorme de parte de todo el equipo."
        )
        msg_encoded = urllib.parse.quote(message)
        url = f"https://api.whatsapp.com/send?phone={phone_formatted}&text={msg_encoded}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_send_email_birthday(self):
        self.ensure_one()
        if not self.email:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'El cliente no tiene un correo registrado.',
                    'type': 'danger',
                    'sticky': False,
                }
            }
            
        message = (
            f"¡Hola, {self.name}!\n\n"
            f"Hoy es una fecha verdaderamente especial, y en nombre de toda la familia de Miss Rose no queríamos dejar pasar la oportunidad de felicitarte en este gran día. "
            f"¡Todo nuestro equipo te desea un MUY FELIZ CUMPLEAÑOS!\n\n"
            f"Esperamos de todo corazón que pases un día extraordinario rodeado de tus seres queridos, lleno de alegría, agradables sorpresas y momentos inolvidables. "
            f"Que este nuevo año de vida venga cargado de muchísima salud, prosperidad, grandes éxitos y toda la energía para que sigas cumpliendo cada una de tus metas.\n\n"
            f"Para nosotros es un honor contar con tu preferencia y nos llena de alegría que seas parte de nuestra familia. Siempre estaremos aquí para ofrecerte lo mejor.\n\n"
            f"¡Disfruta al máximo tu celebración y que sean muchísimos años más! Un abrazo enorme de parte de todo el equipo."
        )
        
        import urllib.parse
        subject = "¡Feliz Cumpleaños de parte de Miss Rose!"
        url = (
            f"https://mail.google.com/mail/?view=cm&fs=1"
            f"&to={self.email}"
            f"&su={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(message)}"
        )
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
