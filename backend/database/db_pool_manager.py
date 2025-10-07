import logging

# Log config
logging.basicConfig(level=logging.INFO)

clients_pool = {}  # client_id: DatabaseConnection

async def get_session_for_database():
    """
    Return a session factory for the given client_name.

    If the session factory has already been created for the client_name, it is
    retrieved from the clients_pool. Otherwise, a new DatabaseConnection is
    created, initialized, and stored in the clients_pool.

    :param client_name: The name of the client.
    :return: A session factory for the given client_name.
    :raises Exception: If there was an error creating or initializing the
        DatabaseConnection.
    """
    try:
        from backend.db_connection.database_connection import DatabaseConnection

        if "database_connection" in clients_pool:
            return clients_pool["database_connection"].get_session_factory()

        db_conn = DatabaseConnection()
        await db_conn.init_db()
        clients_pool["database_connection"] = db_conn
        return db_conn.get_session_factory()
    except Exception as e:
        logging.exception(f"Error in get_session_for_client: {e}")
        raise e