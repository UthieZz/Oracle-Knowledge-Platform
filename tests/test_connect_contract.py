"""Contract tests for OKP Connect interfaces."""
from okc.connect.interfaces import Connector, SyncEvent, HealthStatus


class DummyConnector(Connector):
    name = "dummy"

    def authenticate(self, credentials):
        return True

    def initial_sync(self, tenant_id, silo_id):
        return [SyncEvent(event_id="e1", source="dummy", kind="create", tenant_id=tenant_id, silo_id=silo_id)]

    def incremental_sync(self, cursor, tenant_id, silo_id):
        return []

    def handle_deletion(self, object_id, tenant_id, silo_id):
        return SyncEvent(event_id="del1", source="dummy", kind="delete", tenant_id=tenant_id, silo_id=silo_id)

    def permissions(self, object_id):
        return {"read": True}

    def health(self):
        return HealthStatus.OK


def test_connector_contract():
    c = DummyConnector()
    assert c.authenticate({})
    events = c.initial_sync("t", "s")
    assert len(events) == 1
    assert events[0].kind == "create"
    assert c.health() == HealthStatus.OK
    assert c.permissions("x")["read"] is True
