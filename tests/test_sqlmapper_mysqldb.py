import unittest

from tests.sqlmapper_mysql_common import MySQLMapperTestMixin

try:
    import MySQLdb
except Exception:  # pragma: no cover - depends on local environment
    MySQLdb = None


class TestMySQLdbMapper(MySQLMapperTestMixin, unittest.TestCase):
    DRIVER = MySQLdb
    DRIVER_MISSING_REASON = "MySQLdb (mysqlclient) is not installed"

    @classmethod
    def build_connect_params(cls, env):
        return {
            "host": env["MYSQL_HOST"],
            "port": int(env["MYSQL_PORT"]),
            "user": env["MYSQL_USER"],
            "passwd": env["MYSQL_PASSWORD"],
            "db": env["MYSQL_DATABASE"],
            "autocommit": False,
        }
