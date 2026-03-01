import unittest

from test_sqlmapper_mysql_common import MySQLMapperTestMixin

try:
    import pymysql
except Exception:  # pragma: no cover - depends on local environment
    pymysql = None


class TestPyMySQLMapper(MySQLMapperTestMixin, unittest.TestCase):
    DRIVER = pymysql
    DRIVER_MISSING_REASON = "pymysql is not installed"

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
