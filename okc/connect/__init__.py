"""OKP Connect — replaceable integration layer for silent knowledge capture.

Connectors implement the contract defined here. They produce SyncEvents that
feed the SyncEngine and existing importer/compiler path. Knowledge Core remains
the stable IR.
"""
from .interfaces import Connector, SyncEvent, HealthStatus
from .sync_engine import SyncEngine
from .sync_worker import SyncWorker
from .stub_connector import StubConnector
from .local_folder_connector import LocalFolderConnector
from .knowledge_accumulator import KnowledgeAccumulator

__all__ = [
    "Connector",
    "SyncEvent",
    "HealthStatus",
    "SyncEngine",
    "SyncWorker",
    "StubConnector",
    "LocalFolderConnector",
    "KnowledgeAccumulator",
]
