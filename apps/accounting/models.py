from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum


class Cash(models.Model):
    CURRENCY_TYPE_CHOICES = (('S', 'Soles'), ('E', 'Euros'), ('D', 'Dolares'),)
    CASH_TYPE_CHOICES = (('B', 'Boletaje'), ('E', 'Encomiendas'), ('O', 'Otro'),)
    name = models.CharField('Nombre', max_length=100, unique=True, null=True, blank=True)
    subsidiary = models.ForeignKey('users.Subsidiary', on_delete=models.SET_NULL, null=True, blank=True)
    initial = models.DecimalField(max_digits=10, decimal_places=2, default='0',)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    currency_type = models.CharField('Tipo de moneda', max_length=1, choices=CURRENCY_TYPE_CHOICES, default='S', )
    cash_type = models.CharField('Tipo de caja', max_length=1, choices=CASH_TYPE_CHOICES, default='O', )
    is_bank = models.BooleanField('Es cuenta bancaria', default=False)

    def __str__(self):
        return str(self.name)

    def current_balance(self):
        inputs = 0
        outputs = 0
        opening = 0
        cash_flow_set = CashFlow.objects.filter(cash_id=self.pk)
        initial = self.initial

        if cash_flow_set:
            last_cash_flow_obj = cash_flow_set.last()
            inputs_bank_flow_set = cash_flow_set.filter(type='D').values('type').annotate(totals=Sum('total'))
            outputs_bank_flow_set = cash_flow_set.filter(type='R').values('type').annotate(totals=Sum('total'))

            cash_flow_set = cash_flow_set.filter(transaction_date=last_cash_flow_obj.transaction_date)
            inputs_cash_flow_set = cash_flow_set.filter(type='E').values('transaction_date').annotate(
                totals=Sum('total'))
            outputs_cash_flow_set = cash_flow_set.filter(type='S').values('transaction_date').annotate(
                totals=Sum('total'))
            if self.is_bank:
                if last_cash_flow_obj.type == 'D':
                    if inputs_bank_flow_set:
                        inputs = inputs_bank_flow_set[0].get('totals')
                    opening = initial
                    if outputs_bank_flow_set:
                        outputs = outputs_bank_flow_set[0].get('totals')
                elif last_cash_flow_obj.type == 'R':
                    if outputs_bank_flow_set:
                        outputs = outputs_bank_flow_set[0].get('totals')
                    opening = initial
                    if inputs_bank_flow_set:
                        inputs = inputs_bank_flow_set[0].get('totals')
            else:
                if last_cash_flow_obj.type == 'A':
                    opening = last_cash_flow_obj.total
                elif last_cash_flow_obj.type == 'C':
                    opening = last_cash_flow_obj.total
                elif last_cash_flow_obj.type == 'E':

                    opening_cash_flow_set = cash_flow_set.filter(type='A')
                    if opening_cash_flow_set:
                        opening = opening_cash_flow_set.last().total

                    inputs = inputs_cash_flow_set[0].get('totals')
                    if outputs_cash_flow_set:
                        outputs = outputs_cash_flow_set[0].get('totals')

                elif last_cash_flow_obj.type == 'S':

                    opening_cash_flow_set = cash_flow_set.filter(type='A')
                    if opening_cash_flow_set:
                        opening = opening_cash_flow_set.last().total

                    outputs = outputs_cash_flow_set[0].get('totals')
                    if inputs_cash_flow_set:
                        inputs = inputs_cash_flow_set[0].get('totals')

        else:
            opening = self.initial

        return opening + inputs - outputs


class CashFlow(models.Model):
    DOCUMENT_TYPE_ATTACHED_CHOICES = (
        ('F', 'Factura'), ('B', 'Boleta'), ('T', 'Ticket'), ('V', 'Vale'), ('O', 'Otro'))
    OPERATION_TYPE_CHOICES = (('1', 'Deposito'), ('2', 'Pago electronico'), ('3', 'Compra electronica'), ('4', 'Retiro'), ('5', 'Transferencia bancaria'), ('6', 'Transferencia de Caja a Caja'), ('7', 'Transferencia de Caja a banco'), ('0', 'Ninguno'))
    TYPE_CHOICES = (('A', 'Apertura'), ('C', 'Cierre'), ('E', 'Entrada'), ('S', 'Salida'), ('D', 'Deposito'), ('R', 'Retiro'), ('T', 'Transferencia'),)
    transaction_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    description = models.CharField('Descripcion', max_length=100, null=True, blank=True)
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    n_receipt = models.IntegerField('Numero de Comprobante', default=0, null=True, blank=True)
    document_type_attached = models.CharField('Tipo documento', max_length=1, choices=DOCUMENT_TYPE_ATTACHED_CHOICES,
                                              default='O', )
    type = models.CharField('Tipo de transaccion', max_length=1, choices=TYPE_CHOICES, default='E', )
    subtotal = models.DecimalField('subtotal', max_digits=30, decimal_places=15, default=0)
    total = models.DecimalField('total', max_digits=30, decimal_places=15, default=0)
    igv = models.DecimalField('Igv total', max_digits=30, decimal_places=15, default=0)
    cash = models.ForeignKey(Cash, on_delete=models.SET_NULL, null=True, blank=True)
    operation_code = models.CharField(
        verbose_name='Codigo de operación', max_length=45, null=True, blank=True)
    order = models.ForeignKey('sales.Order', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE, null=True, blank=True)
    operation_type = models.CharField('Tipo operacion', max_length=1, choices=OPERATION_TYPE_CHOICES, default='0', )
    programming = models.ForeignKey('comercial.Programming', on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey('users.Company', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    def return_inputs(self):
        response = 0
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date=self.transaction_date, type='E').values(
            'transaction_date').annotate(totals=Sum('total'))
        if cash_flow_set.count() > 0:
            response = cash_flow_set[0].get('totals')
        return response

    def return_outputs(self):
        response = 0
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date=self.transaction_date, type='S').values(
            'transaction_date').annotate(totals=Sum('total'))
        if cash_flow_set.count() > 0:
            response = cash_flow_set[0].get('totals')
        return response

    def return_balance(self):
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date=self.transaction_date, type='A')
        opening = 0
        if cash_flow_set.count() > 0:
            opening = cash_flow_set.first().total
        response = opening + self.return_inputs() - self.return_outputs()
        return response

    def return_status(self):
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, transaction_date=self.transaction_date, type='C')
        closed = False
        if cash_flow_set.count() > 0:
            closed = True
        return closed

    def return_last_cash_open(self):
        cash_flow_set = CashFlow.objects.filter(cash=self.cash, type='A')
        cash_flow = None
        if cash_flow_set:
            cash_flow = cash_flow_set.last()
        return cash_flow
