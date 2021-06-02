from typing import Generator
from uuid import uuid4

from celery.schedules import crontab
from celery.task import periodic_task
from jsonpath_ng.ext.parser import parse as jsonpath_parse

from corehq import toggles
from corehq.motech.exceptions import RemoteAPIError
from corehq.motech.requests import Requests
from corehq.motech.utils import simplify_list

from .bundle import get_bundle, get_next_url, iter_bundle
from .const import IMPORT_FREQUENCY_DAILY, SYSTEM_URI_CASE_ID
from .models import FHIRImporter, FHIRImporterResourceType


@periodic_task(run_every=crontab(hour=5, minute=5), queue='background_queue')
def run_daily_importers():
    for importer in (
        FHIRImporter.objects.filter(
            frequency=IMPORT_FREQUENCY_DAILY
        ).select_related('connection_settings').all()
    ):
        run_importer(importer)


def run_importer(importer):
    """
    Poll remote API and import resources as CommCare cases.

    ServiceRequest resources are treated specially for workflows that
    handle referrals across systems like CommCare.
    """
    if not toggles.FHIR_INTEGRATION.enabled(importer.domain):
        return
    requests = importer.connection_settings.get_requests()
    # TODO: Check service is online, else retry with exponential backoff
    for resource_type in (
            importer.resource_types
            .filter(import_related_only=False)
            .prefetch_related('jsonpaths_to_related_resource_types')
            .all()
    ):
        import_resource_type(requests, resource_type)


def import_resource_type(
    requests: Requests,
    resource_type: FHIRImporterResourceType,
):
    try:
        for resource in iter_resources(requests, resource_type):
            import_resource(requests, resource_type, resource)
    except Exception as err:
        requests.notify_exception(str(err))


def iter_resources(
    requests: Requests,
    resource_type: FHIRImporterResourceType,
) -> Generator:
    searchset_bundle = get_bundle(
        requests,
        endpoint=f"{resource_type.name}/",
        params=resource_type.search_params,
    )
    while True:
        yield from iter_bundle(searchset_bundle)
        url = get_next_url(searchset_bundle)
        if url:
            searchset_bundle = get_bundle(requests, url=url)
        else:
            break


def import_resource(
    requests: Requests,
    resource_type: FHIRImporterResourceType,
    resource: dict,
):
    if 'resourceType' not in resource:
        raise RemoteAPIError(
            "FHIR resource missing required property 'resourceType'"
        )
    if resource['resourceType'] != resource_type.name:
        raise RemoteAPIError(
            f"API request for resource type {resource_type.name!r} returned "
            f"resource type {resource['resourceType']!r}."
        )

    case_id = uuid4().hex
    if resource_type.name == 'ServiceRequest':
        try:
            resource = claim_service_request(requests, resource, case_id)
        except ServiceRequestNotActive:
            return  # Nothing to do

    # TODO:
    #   * Map resource properties to case properties
    #   * Save case
    import_related(requests, resource_type, resource)


def claim_service_request(requests, service_request, case_id):
    """
    Uses `ETag`_ to prevent a race condition.

    .. _ETag: https://www.hl7.org/fhir/http.html#concurrency
    """
    endpoint = f"ServiceRequest/{service_request['id']}"
    response = requests.get(endpoint, raise_for_status=True)
    etag = response.headers['ETag']
    service_request = response.json()
    if service_request['status'] != 'active':
        raise ServiceRequestNotActive

    service_request['status'] = 'on-hold'
    service_request.setdefault('identifier', [])
    service_request['identifier'].append({
        'system': SYSTEM_URI_CASE_ID,
        'value': case_id,
    })
    headers = {'If-Match': etag}
    response = requests.put(endpoint, json=service_request, headers=headers)
    if 200 <= response.status < 300:
        return service_request
    if response.status == 412:
        # ETag didn't match. Try again.
        return claim_service_request(requests, service_request, case_id)
    else:
        response.raise_for_status()


def get_case_id_or_none(resource):
    """
    If ``resource`` has a CommCare case ID identifier, return its value,
    otherwise return None.
    """
    if 'identifier' in resource:
        case_id_identifier = [id_ for id_ in resource['identifier']
                              if id_.get('system') == SYSTEM_URI_CASE_ID]
        if case_id_identifier:
            return case_id_identifier[0]['value']
    return None


def get_caseblock_kwargs(resource_type, resource):
    reserved = {'case_id', 'external_id', 'owner_id', 'user_id', 'case_type'}
    kwargs = {
        'case_name': get_name(resource),
        'update': {}
    }
    for resource_property in resource_type.properties.all():
        if 'case_property' in resource_property.value_source_config:
            case_property = resource_property.value_source_config['case_property']
            if case_property in reserved:
                continue
            value_source = resource_property.get_value_source()
            value = value_source.get_import_value(resource)
            if value is not None:
                if case_property == 'case_name':
                    kwargs[case_property] = value
                else:
                    kwargs['update'][case_property] = value
    return kwargs


def get_name(resource):
    """
    Returns a name, or a code, or an empty string.
    """
    if resource.get('name'):
        return resource['name'][0].get('text', '')
    if resource.get('code'):
        return resource['code'][0].get('text', '')
    return ''


def import_related(requests, resource_type, resource):
    for rel in resource_type.jsonpaths_to_related_resource_types.all():
        jsonpath = jsonpath_parse(rel.jsonpath)
        reference = simplify_list([x.value for x in jsonpath.find(resource)])
        related_resource = get_resource(requests, reference)
        import_resource(requests, rel.related_resource_type, related_resource)


def get_resource(requests, reference):
    """
    Fetches a resource.

    ``reference`` must be a relative reference. e.g. "Patient/12345"
    """
    response = requests.get(endpoint=reference, raise_for_status=True)
    return response.json()


class ServiceRequestNotActive(Exception):
    pass
