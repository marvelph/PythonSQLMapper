import os
import unittest
from dataclasses import dataclass

from sqlmapper import Mapper, MappingError

try:
    import psycopg2
except Exception:  # pragma: no cover - depends on local environment
    psycopg2 = None


@dataclass
class UserQuery:
    min_id: int
    max_id: int
    status: str


class UserResult:
    def __init__(self):
        self.id = None
        self.name = None


class NewUser:
    def __init__(self, id=None, name=None, status=None):
        self.id = id
        self.name = name
        self.status = status


class UserStatusUpdate:
    def __init__(self, id, status, updated_at):
        self.id = id
        self.status = status
        self.updated_at = updated_at


class UserDeleteParam:
    def __init__(self, id):
        self.id = id


class ResultTypeNeedsArg:
    def __init__(self, value):
        self.value = value


@unittest.skipIf(psycopg2 is None, "psycopg2 is not installed")
class TestPsycopg2Mapper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ
        required = [
            "PGHOST",
            "PGPORT",
            "PGUSER",
            "PGPASSWORD",
            "PGDATABASE",
        ]
        missing = [name for name in required if not env.get(name)]
        if missing:
            raise unittest.SkipTest(
                "PostgreSQL test env is not configured. Missing: {0}".format(", ".join(missing))
            )

        cls.connect_params = {
            "host": env["PGHOST"],
            "port": int(env["PGPORT"]),
            "user": env["PGUSER"],
            "password": env["PGPASSWORD"],
            "dbname": env["PGDATABASE"],
        }

    def setUp(self):
        self.mapper = Mapper(psycopg2, **self.connect_params)
        self._drop_tables()
        self._create_tables()
        self._seed_data()

    def tearDown(self):
        try:
            self._drop_tables()
            self.mapper.commit()
        finally:
            self.mapper.close()

    def _drop_tables(self):
        for table in ("audit_logs", "accounts", "users", "departments", "external_keys"):
            self.mapper.execute("DROP TABLE IF EXISTS {0} CASCADE".format(table))

    def _create_tables(self):
        self.mapper.execute(
            """
            CREATE TABLE departments (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            )
            """
        )
        self.mapper.execute(
            """
            CREATE TABLE users (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(64) NOT NULL,
                updated_at TIMESTAMP NULL,
                department_id BIGINT NULL,
                used_flag SMALLINT NOT NULL DEFAULT 0
            )
            """
        )
        self.mapper.execute(
            """
            CREATE TABLE accounts (
                id BIGINT PRIMARY KEY,
                balance BIGINT NOT NULL
            )
            """
        )
        self.mapper.execute(
            """
            CREATE TABLE audit_logs (
                job_id BIGINT PRIMARY KEY,
                processed SMALLINT NOT NULL DEFAULT 0
            )
            """
        )
        self.mapper.commit()

    def _seed_data(self):
        sales_id = self.mapper.insert("INSERT INTO departments (name) VALUES (:name)", {"name": "Sales"})
        engineering_id = self.mapper.insert(
            "INSERT INTO departments (name) VALUES (:name)", {"name": "Engineering"}
        )

        self.alice_id = self.mapper.insert(
            """
            INSERT INTO users (name, status, updated_at, department_id, used_flag)
            VALUES (:name, :status, :updated_at, :department_id, :used_flag)
            """,
            {
                "name": "Alice",
                "status": "active",
                "updated_at": "2026-03-01 09:00:00",
                "department_id": sales_id,
                "used_flag": 0,
            },
        )
        self.bob_id = self.mapper.insert(
            """
            INSERT INTO users (name, status, updated_at, department_id, used_flag)
            VALUES (:name, :status, :updated_at, :department_id, :used_flag)
            """,
            {
                "name": "Bob",
                "status": "active",
                "updated_at": "2026-03-01 09:00:00",
                "department_id": engineering_id,
                "used_flag": 1,
            },
        )
        self.mapper.insert(
            "INSERT INTO accounts (id, balance) VALUES (:id, :balance)",
            {"id": 1, "balance": 5000},
        )
        self.mapper.insert(
            "INSERT INTO accounts (id, balance) VALUES (:id, :balance)",
            {"id": 2, "balance": 1000},
        )
        self.mapper.insert(
            "INSERT INTO audit_logs (job_id, processed) VALUES (:job_id, :processed)",
            {"job_id": 1, "processed": 0},
        )
        self.mapper.commit()

    def test_select_all_accepts_dataclass_and_dict(self):
        query = UserQuery(min_id=1, max_id=100, status="active")
        rows_from_obj = list(
            self.mapper.select_all(
                """
                SELECT id, name
                  FROM users
                 WHERE id BETWEEN :min_id AND :max_id
                   AND status = :status
                """,
                query,
            )
        )
        rows_from_dict = list(
            self.mapper.select_all(
                """
                SELECT id, name
                  FROM users
                 WHERE id BETWEEN :min_id AND :max_id
                   AND status = :status
                """,
                {"min_id": 1, "max_id": 100, "status": "active"},
            )
        )
        self.assertEqual(len(rows_from_obj), 2)
        self.assertEqual(len(rows_from_dict), 2)

    def test_select_all_works_with_buffered_true_and_false(self):
        rows_buffered = list(
            self.mapper.select_all(
                "SELECT id, name FROM users WHERE status = :status ORDER BY id",
                {"status": "active"},
                array_size=1,
                buffered=True,
            )
        )
        rows_unbuffered = list(
            self.mapper.select_all(
                "SELECT id, name FROM users WHERE status = :status ORDER BY id",
                {"status": "active"},
                array_size=1,
                buffered=False,
            )
        )
        self.assertEqual([row.id for row in rows_buffered], [row.id for row in rows_unbuffered])
        self.assertEqual([row.name for row in rows_buffered], [row.name for row in rows_unbuffered])

    def test_select_one_with_result_type(self):
        row = self.mapper.select_one(
            "SELECT id, name FROM users WHERE id = :id",
            {"id": self.alice_id},
            result_type=UserResult,
        )
        self.assertEqual(row.name, "Alice")

    def test_select_one_returns_none_when_no_rows(self):
        none_row = self.mapper.select_one(
            "SELECT id, name FROM users WHERE id = :id",
            {"id": 99999999},
        )
        self.assertIsNone(none_row)

    def test_select_one_raises_mapping_error_when_multiple_rows(self):
        with self.assertRaises(MappingError):
            self.mapper.select_one(
                "SELECT id, name FROM users WHERE status = :status",
                {"status": "active"},
            )

    def test_select_one_raises_mapping_error_when_result_type_missing_attribute(self):
        with self.assertRaises(MappingError):
            self.mapper.select_one(
                "SELECT id, status FROM users WHERE id = :id",
                {"id": self.alice_id},
                result_type=UserResult,
            )

    def test_select_one_raises_mapping_error_when_bind_variable_missing(self):
        with self.assertRaises(MappingError):
            self.mapper.select_one(
                "SELECT id, name FROM users WHERE id = :id AND status = :status",
                {"id": self.alice_id},
            )

    def test_select_one_raises_mapping_error_when_result_type_requires_args(self):
        with self.assertRaises(MappingError):
            self.mapper.select_one(
                "SELECT id, name FROM users WHERE id = :id",
                {"id": self.alice_id},
                result_type=ResultTypeNeedsArg,
            )

    def test_insert_returns_driver_dependent_lastrowid(self):
        new_user = NewUser(name="Carol", status="active")
        new_user.id = self.mapper.insert(
            "INSERT INTO users (name, status) VALUES (:name, :status)",
            new_user,
        )
        self.assertIn(type(new_user.id), (int, type(None)))

    def test_insert_without_auto_increment_returns_none_or_zero(self):
        self.mapper.execute(
            """
            CREATE TABLE external_keys (
                code VARCHAR(64) PRIMARY KEY
            )
            """
        )
        lastrowid = self.mapper.insert(
            "INSERT INTO external_keys (code) VALUES (:code)",
            {"code": "A001"},
        )
        self.assertIn(lastrowid, (None, 0))

    def test_update_returns_rowcount_for_optimistic_lock_check(self):
        updated_ok = self.mapper.update(
            """
            UPDATE users
               SET status = :status
             WHERE id = :id
               AND updated_at = :updated_at
            """,
            UserStatusUpdate(self.alice_id, "inactive", "2026-03-01 09:00:00"),
        )
        updated_ng = self.mapper.update(
            """
            UPDATE users
               SET status = :status
             WHERE id = :id
               AND updated_at = :updated_at
            """,
            UserStatusUpdate(self.alice_id, "active", "2099-01-01 00:00:00"),
        )
        self.assertEqual(updated_ok, 1)
        self.assertEqual(updated_ng, 0)

    def test_delete_returns_rowcount_with_business_condition(self):
        deleted_bob = self.mapper.delete(
            "DELETE FROM users WHERE id = :id AND used_flag = 0",
            UserDeleteParam(self.bob_id),
        )
        deleted_alice = self.mapper.delete(
            "DELETE FROM users WHERE id = :id AND used_flag = 0",
            UserDeleteParam(self.alice_id),
        )
        self.assertEqual(deleted_bob, 0)
        self.assertEqual(deleted_alice, 1)

    def test_execute_can_run_special_sql(self):
        self.mapper.execute("ALTER TABLE users ADD COLUMN profile TEXT NULL")
        self.mapper.commit()
        row = self.mapper.select_one(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_name = :table_name
               AND column_name = :column_name
            """,
            {"table_name": "users", "column_name": "profile"},
        )
        self.assertIsNotNone(row)

    def test_transaction_commit_and_explicit_rollback_on_reused_mapper(self):
        self.mapper.update(
            "UPDATE accounts SET balance = balance - :amount WHERE id = :from_id",
            {"amount": 1000, "from_id": 1},
        )
        self.mapper.update(
            "UPDATE accounts SET balance = balance + :amount WHERE id = :to_id",
            {"amount": 1000, "to_id": 2},
        )
        self.mapper.commit()

        try:
            self.mapper.update(
                "UPDATE users SET status = :status WHERE id = :id",
                {"id": self.bob_id, "status": "inactive"},
            )
            self.mapper.update(
                "UPDATE audit_logs SET processed = 1 WHERE job_id = :job_id",
                {"job_id": 1},
            )
            raise RuntimeError("simulate failure")
        except Exception:
            self.mapper.rollback()

        account1 = self.mapper.select_one("SELECT id, balance FROM accounts WHERE id = :id", {"id": 1})
        account2 = self.mapper.select_one("SELECT id, balance FROM accounts WHERE id = :id", {"id": 2})
        bob = self.mapper.select_one("SELECT id, status FROM users WHERE id = :id", {"id": self.bob_id})
        log = self.mapper.select_one("SELECT job_id, processed FROM audit_logs WHERE job_id = :job_id", {"job_id": 1})
        self.assertEqual(account1.balance, 4000)
        self.assertEqual(account2.balance, 2000)
        self.assertEqual(bob.status, "active")
        self.assertEqual(log.processed, 0)

    def test_uncommitted_changes_are_rolled_back_when_exiting_with_by_exception(self):
        with self.assertRaises(RuntimeError):
            with Mapper(psycopg2, **self.connect_params) as mapper:
                mapper.update(
                    "UPDATE users SET status = :status WHERE id = :id",
                    {"id": self.bob_id, "status": "inactive"},
                )
                raise RuntimeError("simulate failure")

        with Mapper(psycopg2, **self.connect_params) as checker:
            user = checker.select_one(
                "SELECT id, status FROM users WHERE id = :id",
                {"id": self.bob_id},
            )
        self.assertEqual(user.status, "active")


if __name__ == "__main__":
    unittest.main()
