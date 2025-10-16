"""Payments API views.

This module exposes CRUD endpoints for payments.
The base path is configured via the DRF router in `apps.payments.urls`.

Authentication:
- Requires token (Knox).

Pagination:
- Page-number pagination.
- Query params: `page`, `page_size` (default 20, max 100).

Notes:
- Only Credit remits produce payments. Cash/Work remits will yield an empty list when filtering by a Cash/Work remit id.
"""
from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer
from apps.sales.models import Credit
from shared.viewsets.tenant_viewsets import TenantAuditModelViewSet


class StandardResultsSetPagination(PageNumberPagination):
    """Default pagination for payments lists.

    Query parameters:
    - page: Page number (default: 1).
    - page_size: Items per page (default: 20, max: 100).
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 40


class PaymentViewSet(TenantAuditModelViewSet):
    """
    List, retrieve, create, update and delete payments.

    Endpoints (actual paths depend on the router registration in `apps.payments.urls`):
    - GET    /api/payments/…/               → List all payments (paginated)
    - GET    /api/payments/…/?remit_id=123  → List payments for a specific remit (paginated)
    - GET    /api/payments/{id}/            → Retrieve
    - POST   /api/payments/                 → Create
    - PATCH  /api/payments/{id}/            → Partial update
    - DELETE /api/payments/{id}/            → Delete

    Query parameters:
    - remit_id (optional): Remit ID to filter payments by. Only Credit remits have payments.
    - page (optional): Page number.
    - page_size (optional): Items per page.

    Response:
    - Paginated result with `count`, `next`, `previous`, and `results` (array of payments).
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """Return a queryset of payments, optionally filtered by remit id.

        Filtering:
        - If `remit_id` is present, the queryset is filtered by `sale_id=<remit_id>`.
          Note: `Payment.sale` references a Credit remit; Cash/Work remits have no payments.

        Ordering:
        - Newest payments first (by creation timestamp).
        """
        qs = Payment.objects.select_related('sale', 'created_by').order_by('-created')
        remit_id = self.request.query_params.get('remit_id')
        if remit_id:
            qs = qs.filter(sale_id=remit_id)
        return qs

    def perform_create(self, serializer):
        """
        Bind the payment to a Credit remit and to the authenticated user.
        Expected payload:
        {
            "sale_id": 1,
            "amount": "100.00",
            "payment_method": "1"
        }
        """
        sale_id = self.request.data.get('sale_id')
        credit_sale = get_object_or_404(Credit, id=sale_id)
        try:
            serializer.save(sale=credit_sale, created_by=self.request.user)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages)

    def update(self, request, *args, **kwargs):
        """Only allow updating mutable fields: amount, payment_method."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        allowed_fields = ['amount', 'payment_method']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_update(serializer)
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)