import unittest

from test_sqlmapper_mysql_common import MySQLMapperTestMixin

try:
    import mysql.connector as mysql_connector
except Exception:  # pragma: no cover - depends on local environment
    mysql_connector = None


class TestMySQLConnectorMapper(MySQLMapperTestMixin, unittest.TestCase):
    DRIVER = mysql_connector
    DRIVER_MISSING_REASON = "mysql.connector is not installed"

    @classmethod
    def build_connect_params(cls, env):
        return {
            "host": env["MYSQL_HOST"],
            "port": int(env["MYSQL_PORT"]),
            "user": env["MYSQL_USER"],
            "password": env["MYSQL_PASSWORD"],
            "database": env["MYSQL_DATABASE"],
            "autocommit": False,
        }
