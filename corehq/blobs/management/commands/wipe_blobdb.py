import asyncio

from django.core.management import BaseCommand

from corehq.apps.cleanup.utils import confirm_destructive_operation
from corehq.blobs import get_blob_db
from corehq.blobs.models import BlobMeta
from corehq.sql_db.util import get_db_aliases_for_partitioned_query
from dimagi.utils.chunked import chunked

CHUNK_SIZE = 1000


class Command(BaseCommand):
    """
    Wipe all data from BlobDB.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            dest='commit',
            default=False,
        )

    def handle(self, *args, **options):
        confirm_destructive_operation()

        # Python 3.7+
        # bytes_deleted = asyncio.run(wipe_blobdb(options['commit']))

        # Python 3.4+
        loop = asyncio.get_event_loop()
        try:
            future = wipe_blobdb(options['commit'])
            bytes_deleted = loop.run_until_complete(future)
        finally:
            loop.close()

        print(f"Deleted {bytes_deleted} bytes.")
        if not options['commit']:
            print("You need to run with --commit for the deletion to happen.")


async def wipe_blobdb(commit=False):
    """
    Wipe shards in parallel
    """
    coros = [wipe_shard(dbname, commit)
             for dbname in get_db_aliases_for_partitioned_query()]
    bytes_deleted_list = await asyncio.gather(*coros)
    return sum(bytes_deleted_list)


async def wipe_shard(dbname, commit=False):
    bytes_deleted = 0
    metas = BlobMeta.objects.using(dbname).all()
    for chunk in chunked(metas, CHUNK_SIZE):
        if commit:
            await wipe_chunk(chunk)
        bytes_deleted += sum(meta.content_length for meta in chunk)
    return bytes_deleted


async def wipe_chunk(chunk):
    """
    An awaitable blob_db.bulk_delete() not to hold up the event loop
    """
    blob_db = get_blob_db()
    blob_db.bulk_delete(metas=chunk)
