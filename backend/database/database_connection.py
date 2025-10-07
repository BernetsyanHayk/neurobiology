"""
This file contains Async SQLAlchemy database connection manager with session management and environment-based configuration.
"""
import os, logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, scoped_session
import backend.global_variables as configs


logging.basicConfig(level=logging.INFO)


class DatabaseConnection:
    def __init__(self):
        """
        Initialize the DatabaseConnection object with a given configuration.

        :param config: Configuration for the database connection.
        :type config: str
        """
        self.engine = None
        self.session_factory = None
        
    async def init_db(self):
        """
        Initialize the database connection with the given environment configuration.

        This method sets up the asynchronous SQLAlchemy engine and session factory
        based on the provided environment configuration. If the environment is not
        specified, it defaults to using the configuration passed during the instantiation
        of the DatabaseConnection object.

        :param environment: The environment key to retrieve the database configuration.
                            If None, the default configuration of the object is used.
        :type environment: str
        """
        logging.info(f"Initializing database connection")
        configs.load_dbconfig()
        dbConfig = configs.DBCONFIG["default_connection"]
        if not dbConfig:
            raise Exception(f"Invalid connection: {dbConfig}, cant connect to the database")

        dbUrl = (
            f"postgresql+asyncpg://{dbConfig['user']}:{dbConfig['password']}"
            f"@{dbConfig['host']}:{dbConfig['port']}/{dbConfig['database']}"
        )

        self.engine = create_async_engine(
            dbUrl,
            pool_size=10,
            max_overflow=5,
        )
        
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def get_session(self):
        """
        Retrieve a scoped session using the current session factory.
        """
        return scoped_session(self.session_factory)

    def get_session_factory(self):
        return self.session_factory
    
    async def check_session(self):
        """
        Check and retrieve the current session factory.
        """
        try:
            if self.session_factory is not None:
                return self.session_factory
            else:
                return None
        except Exception:
            return None

    async def check_engine(self):
        """
        Check and retrieve the current SQLAlchemy engine.
        """
        try:
            if self.engine is not None:
                return self.engine
            else:
                return None
        except Exception:
            return None


load_dotenv()
configName = os.getenv('SERVER_CONFIG')

database_connection = DatabaseConnection(configName)
# Use 'session' for database operations
# Remember to close the session when done: session.close()
