import logging
from functools import wraps

from django.http import HttpResponseForbidden

from dimagi.utils.couch.cache.cache_core import get_redis_client

from corehq.apps.domain.models import Domain
from corehq.apps.users.decorators import require_permission
from corehq.apps.users.models import Permissions

auth_logger = logging.getLogger("commcare_auth")

ORIGIN_TOKEN_HEADER = 'HTTP_X_COMMCAREHQ_ORIGIN_TOKEN'
ORIGIN_TOKEN_SLUG = 'OriginToken'


def require_mobile_access(fn):
    @wraps(fn)
    def _inner(request, domain, *args, **kwargs):
        if Domain.get_by_name(domain).restrict_mobile_access:
            origin_token = request.META.get(ORIGIN_TOKEN_HEADER, None)
            if origin_token:
                if _test_token_valid(origin_token):
                    return fn(request, domain, *args, **kwargs)
                else:
                    auth_logger.info(
                        "Request rejected domain=%s reason=%s request=%s",
                        domain, "flag:mobile_access_restricted", request.path
                    )
                    return HttpResponseForbidden()

            return require_permission(Permissions.access_mobile_endpoints)(fn)(request, domain, *args, **kwargs)

        return fn(request, domain, *args, **kwargs)

    return _inner


def _test_token_valid(origin_token):
    client = get_redis_client().client.get_client()
    test_result = client.get("%s%s" % (ORIGIN_TOKEN_SLUG, origin_token))
    if test_result:
        return test_result.decode("UTF-8") == '"valid"'

    return False
