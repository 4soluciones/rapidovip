import graphene

from graphene_django import DjangoObjectType

from django.contrib.auth.models import User

from apps.sales.models import (
    Order, OrderDetail, OrderRoute, OrderAction, OrderAddressee, Client, Unit,
    TYPE_COMMODITY_CHOICES, GUIDE_TYPE_CHOICES, STATUS_TRANSPORT_CHOICES,
    TYPE_DOCUMENT, SERVICE_TYPE_CHOICES, WAY_TO_PAY_CHOICES,
)

from apps.users.models import Company, Subsidiary

from apps.comercial.models import Truck


class ClientType(DjangoObjectType):
    class Meta:
        model = Client
        fields = '__all__'


class UnitType(DjangoObjectType):
    class Meta:
        model = Unit
        fields = '__all__'


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = '__all__'


class CompanyType(DjangoObjectType):
    class Meta:
        model = Company
        fields = '__all__'


class TruckType(DjangoObjectType):
    class Meta:
        model = Truck
        fields = '__all__'


class ComercialSubsidiaryType(DjangoObjectType):
    class Meta:
        model = Subsidiary
        fields = '__all__'


class SalesOrderType(DjangoObjectType):
    way_to_pay_readable = graphene.String()
    type_commodity_readable = graphene.String()
    type_document_readable = graphene.String()
    type_guide_readable = graphene.String()
    status_transport_readable = graphene.String()
    service_type_readable = graphene.String()

    class Meta:
        model = Order
        fields = '__all__'

    def resolve_way_to_pay_readable(self, info):
        return dict(WAY_TO_PAY_CHOICES).get(self.way_to_pay)

    def resolve_type_commodity_readable(self, info):
        encomienda = getattr(self, 'encomienda', None)
        if not encomienda:
            return None
        return dict(TYPE_COMMODITY_CHOICES).get(encomienda.type_commodity)

    def resolve_type_document_readable(self, info):
        return dict(TYPE_DOCUMENT).get(self.type_document)

    def resolve_type_guide_readable(self, info):
        encomienda = getattr(self, 'encomienda', None)
        if not encomienda:
            return None
        return dict(GUIDE_TYPE_CHOICES).get(encomienda.type_guide)

    def resolve_status_transport_readable(self, info):
        encomienda = getattr(self, 'encomienda', None)
        if not encomienda:
            return None
        return dict(STATUS_TRANSPORT_CHOICES).get(encomienda.status_transport)

    def resolve_service_type_readable(self, info):
        return dict(SERVICE_TYPE_CHOICES).get(self.service_type)


class SalesOrderDetailType(DjangoObjectType):
    class Meta:
        model = OrderDetail
        fields = '__all__'


class SalesOrderRouteType(DjangoObjectType):
    class Meta:
        model = OrderRoute
        fields = '__all__'


class SalesOrderActionType(DjangoObjectType):
    class Meta:
        model = OrderAction
        fields = '__all__'


class SalesOrderAddresseeType(DjangoObjectType):
    class Meta:
        model = OrderAddressee
        fields = '__all__'


class OrderQueryResultType(graphene.ObjectType):
    order = graphene.Field(SalesOrderType)
    order_details = graphene.List(SalesOrderDetailType)
    order_routes = graphene.List(SalesOrderRouteType)
    order_actions = graphene.List(SalesOrderActionType)
    order_addressees = graphene.List(SalesOrderAddresseeType)


class Query(graphene.ObjectType):
    order_by_id_and_code_track = graphene.Field(
        OrderQueryResultType,
        id=graphene.Int(required=True),
        code_track=graphene.String(required=True)
    )

    def resolve_order_by_id_and_code_track(self, info, id, code_track):
        try:
            order = Order.objects.select_related(
                'client', 'subsidiary', 'user', 'truck', 'company'
            ).get(id=id, encomienda__code_track=code_track)

            order_details = OrderDetail.objects.select_related(
                'unit'
            ).filter(order=order)

            order_routes = OrderRoute.objects.select_related(
                'subsidiary'
            ).filter(order=order)

            order_actions = OrderAction.objects.select_related(
                'client', 'order_addressee'
            ).filter(order=order)

            order_addressees = OrderAddressee.objects.filter(
                orderaction__order=order
            ).distinct()

            return OrderQueryResultType(
                order=order,
                order_details=order_details,
                order_routes=order_routes,
                order_actions=order_actions,
                order_addressees=order_addressees
            )
        except Order.DoesNotExist:
            return None


schema = graphene.Schema(query=Query)
