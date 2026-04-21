"""MongoDB-backed database bootstrap wrapping existing init_db behaviour."""
from app.domain.contracts.database_bootstrap import DatabaseBootstrap


class MongoBootstrap(DatabaseBootstrap):
    """Mongo implementation — delegates to the existing ``init_db`` module."""

    def bootstrap(self) -> None:
        from app.init_db import initialize_databases
        initialize_databases()
