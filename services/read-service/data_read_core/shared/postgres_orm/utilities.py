import sys
from contextlib import asynccontextmanager

from asgiref.sync import sync_to_async
from django.db import transaction


@asynccontextmanager
async def aatomic(using=None):
    atom = transaction.atomic(using=using)
    await sync_to_async(atom.__enter__, thread_sensitive=True)()
    try:
        yield
    except Exception:
        await sync_to_async(atom.__exit__, thread_sensitive=True)(*sys.exc_info())
        raise
    else:
        await sync_to_async(atom.__exit__, thread_sensitive=True)(None, None, None)
