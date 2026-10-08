from time import monotonic, sleep

from sqlalchemy import Engine, text


def wait_for_database_lock(engine: Engine, query_fragment: str) -> bool:
    lock_deadline = monotonic() + 5
    while monotonic() < lock_deadline:
        with engine.connect() as connection:
            waiting_updates = connection.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE wait_event_type='Lock' "
                    "AND pid <> pg_backend_pid() AND query LIKE :query_pattern"
                ),
                {"query_pattern": f"%{query_fragment}%"},
            )
        if waiting_updates:
            return True
        sleep(0.01)
    return False
