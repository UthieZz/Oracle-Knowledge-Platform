"""OKP Connect — replaceable integration layer for silent knowledge capture.

Connectors implement the contract defined here. They produce KnowledgePackage
fragments or events that feed the existing ingestion/compiler path. Knowledge
Core remains the stable IR.
"""
from .interfaces import Connector, SyncEvent, HealthStatus
from .sync_engine import SyncEngine

__all__ = ["Connector", "SyncEvent", "HealthStatus", "SyncEngine"]
