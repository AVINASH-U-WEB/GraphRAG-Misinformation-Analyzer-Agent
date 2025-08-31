# backend/services/neo4j_service.py
from neo4j import GraphDatabase, Driver, exceptions
from config import Config
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jService:
    _instance = None
    _driver: Driver = None
    _connection_attempts = 0
    _max_connection_attempts = 5
    _retry_delay_seconds = 5

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jService, cls).__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        if self._driver is None:
            while self._connection_attempts < self._max_connection_attempts:
                try:
                    self._driver = GraphDatabase.driver(
                        Config.NEO4J_URI,
                        auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD),
                        max_connection_lifetime=600,
                        connection_acquisition_timeout=60
                    )
                    self._driver.verify_connectivity()
                    logger.info("Successfully connected to Neo4j AuraDB.")
                    self._create_constraints()
                    self._connection_attempts = 0
                    return
                except exceptions.ServiceUnavailable as e:
                    logger.warning(f"Neo4j service unavailable, retrying in {self._retry_delay_seconds}s... ({e})")
                    self._connection_attempts += 1
                    time.sleep(self._retry_delay_seconds)
                except Exception as e:
                    logger.error(f"Failed to connect to Neo4j on attempt {self._connection_attempts+1}: {e}")
                    self._connection_attempts += 1
                    time.sleep(self._retry_delay_seconds)
            
            logger.error("Exceeded max connection attempts to Neo4j. Driver remains None.")
            self._driver = None

    def _create_constraints(self):
        if not self._driver:
            logger.warning("No Neo4j driver available, skipping constraint creation.")
            return
        with self._driver.session() as session:
            try:
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Timestamp) REQUIRE t.value IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Claim) REQUIRE c.text IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.text IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (h:Hashtag) REQUIRE h.tag IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (v:FactCheckVerdict) REQUIRE v.value IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:FactCheckSource) REQUIRE s.name IS UNIQUE"
                ]
                for constraint in constraints:
                    session.run(constraint)
                logger.info("Neo4j constraints created/verified.")
            except Exception as e:
                logger.error(f"Failed to create Neo4j constraints: {e}")

    def get_driver(self) -> Driver:
        if self._driver is None:
            logger.warning("Neo4j driver is None, attempting to reconnect.")
            self._connect()
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed.")
            self._connection_attempts = 0

    @staticmethod
    def _execute_query(tx, query, parameters=None):
        result = tx.run(query, parameters or {})
        return [record for record in result]

    def run_query(self, query: str, parameters: dict = None):
        driver = self.get_driver()
        if not driver:
            raise ConnectionError("Neo4j driver is not available.")
        try:
            with driver.session() as session:
                return session.execute_write(self._execute_query, query, parameters)
        except exceptions.ClientError as e:
            logger.error(f"Neo4j ClientError (Cypher Syntax, etc.): {e}\nQuery: {query}\nParams: {parameters}")
            raise
        except exceptions.ServiceUnavailable as e:
            logger.warning(f"Neo4j service unavailable during query. ({e})")
            self.close()
            raise ConnectionError(f"Service unavailable, connection has been reset. Please retry the operation.")
        except Exception as e:
            logger.error(f"General error executing Cypher query: {e}")
            raise

neo4j_service = Neo4jService()