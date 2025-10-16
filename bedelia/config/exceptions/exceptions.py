from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import set_rollback, exception_handler


def global_exception_handler(exc, context):
    if isinstance(exc, ValidationError):
        set_rollback()
        if isinstance(exc.detail, dict):
            payload = {**exc.detail, "detail": exc.detail}
            return Response(payload, status=exc.status_code)
        return Response({"detail": exc.detail}, status=exc.status_code)

    if isinstance(exc, APIException):
        headers = {}
        if getattr(exc, "auth_header", None):
            headers["WWW-Authenticate"] = exc.auth_header
        if getattr(exc, "wait", None):
            headers["Retry-After"] = "%d" % exc.wait
        data = {"detail": exc.detail}
        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    if isinstance(exc, ProtectedError):
        data = {"detail": exc.args[0]}
        set_rollback()
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    return exception_handler(exc, context)
