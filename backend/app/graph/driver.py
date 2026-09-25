from functools import cache

from neo4j import Driver, GraphDatabase

from .. import config


@cache
def get_driver() -> Driver:
    return GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
