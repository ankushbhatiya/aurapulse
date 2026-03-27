import os
from neo4j import GraphDatabase
from api.config import settings
from api.logger import logger

class Neo4jConnector:
    _instance = None
    _driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jConnector, cls).__new__(cls)
        return cls._instance

    def get_driver(self):
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD) if settings.NEO4J_PASSWORD else None
                )
                self._driver.verify_connectivity()
                logger.info("Neo4j driver initialized and connectivity verified.")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j driver: {e}")
                raise
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed.")

neo4j_connector = Neo4jConnector()
