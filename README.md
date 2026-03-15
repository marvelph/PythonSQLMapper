# PythonSQLMapper

[English](README.md) | [日本語](README.ja.md)

PythonSQLMapper is a small library that maps SQL results to Python objects.  
It follows a design philosophy similar to [iBATIS](https://ibatis.apache.org), with a focus on keeping things simple.

- Supported DBs: MySQL / PostgreSQL / SQLite
- Python: 3.10+

Originally, this project was a Python reimplementation of [CocoaSQLMapper](https://github.com/marvelph/CocoaSQLMapper) for iOS/macOS.

## Installation

```bash
pip install PythonSQLMapper
```

## Basic Usage

### 1. Create a Mapper

Pass a DB-API compatible driver and connection parameters to `Mapper(driver, **connect_params)`.

```python
import sqlite3
from sqlmapper import Mapper

mapper = Mapper(sqlite3, database="sample.db")
```

Call `close()` explicitly at the end of your process to close the connection.

```python
import sqlite3
from sqlmapper import Mapper

mapper = Mapper(sqlite3, database="sample.db")
try:
    user = mapper.select_one(
        "SELECT id, name FROM users WHERE id = :id",
        {"id": 1},
    )
finally:
    mapper.close()
```

You can also use `with`.

```python
import sqlite3
from sqlmapper import Mapper

with Mapper(sqlite3, database="sample.db") as mapper:
    user = mapper.select_one(
        "SELECT id, name FROM users WHERE id = :id",
        {"id": 1},
    )
```

### 2. Use Named Bind Variables

Use `:name` placeholders in SQL.  
Parameters can be passed as an object with attributes or as a `dict`.  
You can use `dataclass` for the object form.

```python
from dataclasses import dataclass

@dataclass
class UserQuery:
    min_id: int
    max_id: int
    status: str

query = UserQuery(min_id=1, max_id=100, status="active")
users = mapper.select_all(
    """
    SELECT id, name
      FROM users
     WHERE id BETWEEN :min_id AND :max_id
       AND status = :status
    """,
    query,
)
```

```python
users = mapper.select_all(
    """
    SELECT id, name
      FROM users
     WHERE id BETWEEN :min_id AND :max_id
       AND status = :status
    """,
    {"min_id": 1, "max_id": 100, "status": "active"},
)
```
We recommend using `dict` for one-off use, and `dataclass` when you want to reuse query parameters.

### 3. Receive Results

- With `result_type`: rows are mapped to instances of the specified class  
  (a `MappingError` is raised if a column has no matching attribute)
- Without `result_type`: a dynamic object (`sqlmapper.Result`) is returned
- Input parameter class and result class can be the same or different
- `result_type` is instantiated as `result_type()`, so it must be no-arg constructible
- `result_type` can be a normal class or a `dataclass`

We recommend specifying `result_type` so column/attribute mismatches are checked.  
For joins and aggregations where defining a dedicated class is too much, you can omit `result_type` and use the dynamic object.

```python
class User:
    def __init__(self):
        self.id = None
        self.name = None

user = mapper.select_one(
    "SELECT id, name FROM users WHERE id = :id",
    {"id": 1},
    result_type=User,
)
```

```python
rows = mapper.select_all(
    """
    SELECT
        u.id          AS user_id,
        u.name        AS user_name,
        d.name        AS dept_name
      FROM users u
      JOIN departments d ON d.id = u.department_id
     WHERE u.status = :status
    """,
    {"status": "active"},
)

for row in rows:
    print(row.user_id, row.user_name, row.dept_name)
```

Resolve same-name column conflicts using `AS` in SQL.  
With the dynamic object you can access `row.user_id`. If you use `result_type`, define matching attributes on the class.

### 4. Use `lastrowid` from `insert` as Model ID

`insert` accepts a model instance as well as a `dict`.  
The return value is the driver’s `lastrowid`, which you can assign to the model `id`.

```python
class User:
    def __init__(self, id=None, name=None, status=None):
        self.id = id
        self.name = name
        self.status = status

new_user = User(name="Alice", status="active")
new_user.id = mapper.insert(
    "INSERT INTO users (name, status) VALUES (:name, :status)",
    new_user,
)
print(new_user.id)

mapper.commit()
```

### 5. Use `rowcount` from `update` for Optimistic Locking

`update` returns the driver’s `rowcount`.  
You can use it to check whether exactly one row was updated, which is useful for optimistic locking (e.g., `updated_at`/`version` in the `WHERE` clause).

```python
class UserStatusUpdate:
    def __init__(self, id, status, updated_at):
        self.id = id
        self.status = status
        self.updated_at = updated_at

param = UserStatusUpdate(
    id=1,
    status="inactive",
    updated_at="2026-03-01 09:00:00",
)
updated = mapper.update(
    """
    UPDATE users
       SET status = :status
     WHERE id = :id
       AND updated_at = :updated_at
    """,
    param,
)

if updated != 1:
    raise RuntimeError("Update failed due to a conflict.")

mapper.commit()
```

### 6. Delete Only When Conditions Are Met

`delete` returns the driver’s `rowcount`.  
By adding business conditions (e.g., `used_flag = 0`) you can detect failed deletes caused by concurrent changes.

```python
class UserDeleteParam:
    def __init__(self, id):
        self.id = id

param = UserDeleteParam(id=1)
deleted = mapper.delete(
    """
    DELETE FROM users
     WHERE id = :id
       AND used_flag = 0
    """,
    param,
)

if deleted != 1:
    raise RuntimeError("Delete failed or the record does not exist.")

mapper.commit()
```

### 7. Use `execute` for Special SQL

Use `execute` for DDL (`ALTER TABLE`, etc.) or SQL that does not fit `insert` / `update` / `delete` / `select`.  
`execute` returns nothing, so call `commit()` if needed.

```python
mapper.execute(
    "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL"
)
mapper.commit()
```

### 8. Control Transactions

With autocommit disabled, changes after `Mapper` creation remain uncommitted until `commit()`.  
To keep writes atomic, group multiple updates and finalize with `commit()`.  
`commit()` can be called multiple times, so you can run multiple transactions on one connection.  
If an exception escapes a `with` block before `commit()`, changes are uncommitted and rolled back per driver behavior.

- With `with`: uncommitted changes roll back on exit (the driver handles rollback when the connection closes; `Mapper` does not call `rollback()` explicitly)
- With a reused `Mapper`: explicitly call `rollback()` after failure to avoid carrying an uncommitted state into the next operation

```python
with Mapper(sqlite3, database="sample.db") as mapper:
    mapper.update(
        "UPDATE accounts SET balance = balance - :amount WHERE id = :from_id",
        {"amount": 1000, "from_id": 1},
    )
    mapper.update(
        "UPDATE accounts SET balance = balance + :amount WHERE id = :to_id",
        {"amount": 1000, "to_id": 2},
    )
    mapper.commit()
```

```python
# mapper: a Mapper instance reused across jobs
# jobs: iterable of jobs to process
for job in jobs:
    try:
        mapper.update(
            "UPDATE users SET status = :status WHERE id = :id",
            {"id": job.user_id, "status": "inactive"},
        )
        mapper.update(
            "UPDATE audit_logs SET processed = 1 WHERE job_id = :job_id",
            {"job_id": job.id},
        )
        mapper.commit()
    except Exception:
        mapper.rollback()  # reset a reused connection before the next job
        continue
```

## API

### `select_one(sql, parameter=None, result_type=None)`

- Fetch one row
- Returns `None` if no rows
- Raises `MappingError` if multiple rows are returned

### `select_all(sql, parameter=None, result_type=None, array_size=1, buffered=True)`

- Fetch multiple rows (`yield` per row)
- `buffered=True`: reads all rows into memory before returning
- `buffered=False`: reads in `array_size` chunks

Behavior with `buffered=False` depends on the driver.

- sqlite3: ignored
- mysql / MySQLdb / pymysql: cannot execute the next SQL on the same connection while unread rows remain
- psycopg2: can execute another SQL within the same transaction

**Cursors used internally**

| Driver | buffered=True | buffered=False |
| --- | --- | --- |
| sqlite3 | - | - |
| mysql.connector | dictionary, buffered | dictionary |
| MySQLdb / pymysql | DictCursor | SSDictCursor |
| psycopg2 | RealDictCursor | RealDictCursor (named) |

```python
for user in mapper.select_all(
    "SELECT id, name FROM users WHERE status = :status",
    {"status": "active"},
    array_size=100,
):
    print(user.id, user.name)
```

### `insert(sql, parameter=None)`

- Execute INSERT
- Returns the driver’s `lastrowid`

```python
class NewUser:
    def __init__(self, name, status, id=None):
        self.id = id
        self.name = name
        self.status = status

new_user = NewUser(name="Alice", status="active")
new_user.id = mapper.insert(
    "INSERT INTO users (name, status) VALUES (:name, :status)",
    new_user,
)
print(new_user.id)
```

`lastrowid` semantics depend on the driver implementation.  
Depending on the database, you may need a different key retrieval method (e.g., PostgreSQL `RETURNING`).

### `update(sql, parameter=None)`

- Execute UPDATE
- Returns the driver’s `rowcount`

```python
class UserStatusUpdate:
    def __init__(self, id, status):
        self.id = id
        self.status = status

count = mapper.update(
    "UPDATE users SET status = :status WHERE id = :id",
    UserStatusUpdate(id=1, status="inactive"),
)
```

### `delete(sql, parameter=None)`

- Execute DELETE
- Returns the driver’s `rowcount`

```python
deleted = mapper.delete(
    "DELETE FROM users WHERE id = :id AND used_flag = 0",
    {"id": 1},
)
```

### `upsert(sql, parameter=None)`

- Execute UPSERT
- `upsert` returns `(rowcount, lastrowid)` from the driver

```python
# MySQL
rowcount, lastrowid = mapper.upsert(
    """
    INSERT INTO users (id, name, status)
    VALUES (:id, :name, :status)
    ON DUPLICATE KEY UPDATE name = VALUES(name), status = VALUES(status)
    """,
    {"id": 1, "name": "Alice", "status": "active"},
)
```

```python
# SQLite3 / PostgreSQL
rowcount, lastrowid = mapper.upsert(
    """
    INSERT INTO users (id, name, status)
    VALUES (:id, :name, :status)
    ON CONFLICT(id) DO UPDATE SET name = excluded.name, status = excluded.status
    """,
    {"id": 1, "name": "Alice", "status": "active"},
)
```

Interpretation of `(rowcount, lastrowid)` depends on the driver implementation.

### `ignore(sql, parameter=None)`

- Execute SQL that ignores duplicates
- `ignore` is an alias of `upsert` and returns `(rowcount, lastrowid)`

```python
# MySQL
rowcount, lastrowid = mapper.ignore(
    """
    INSERT IGNORE INTO users (id, name, status)
    VALUES (:id, :name, :status)
    """,
    {"id": 1, "name": "Alice", "status": "active"},
)
```

```python
# SQLite3 / PostgreSQL
rowcount, lastrowid = mapper.ignore(
    """
    INSERT INTO users (id, name, status)
    VALUES (:id, :name, :status)
    ON CONFLICT(id) DO NOTHING
    """,
    {"id": 1, "name": "Alice", "status": "active"},
)
```

### `execute(sql, parameter=None)`

- Execute arbitrary SQL
- No return value

```python
mapper.execute(
    "ALTER TABLE users ADD COLUMN profile TEXT"
)
mapper.commit()
```

### `returning_one(sql, parameter=None, result_type=None)` / `returning_all(...)`

- Alias of `select_one` / `select_all`
- Use for `RETURNING` clauses or SQL that returns result sets

```python
# PostgreSQL: INSERT ... RETURNING
class NewUser:
    def __init__(self, name, status, id=None):
        self.id = id
        self.name = name
        self.status = status

new_user = NewUser(name="Alice", status="active")
new_user.id = mapper.returning_one(
    "INSERT INTO users (name, status) VALUES (:name, :status) RETURNING id",
    new_user,
).id
print(new_user.id)
```

```python
# UPDATE ... RETURNING (multiple rows)
rows = mapper.returning_all(
    "UPDATE users SET status = :status WHERE status = :old_status RETURNING id, status",
    {"status": "inactive", "old_status": "active"},
)
for row in rows:
    print(row.id, row.status)
```

```python
# Stored procedure / function (single row)
row = mapper.returning_one(
    "SELECT get_user_count(:status) AS count",
    {"status": "active"},
)
print(row.count)
```

```python
# Stored procedure / function (multiple rows)
rows = mapper.returning_all(
    "SELECT id, name FROM get_active_users(:status)",
    {"status": "active"},
)
for row in rows:
    print(row.id, row.name)
```

### `commit()` / `rollback()` / `close()`

- `commit()` finalizes the current transaction
- `rollback()` discards the current transaction
- `close()` closes the connection (uncommitted changes are rolled back per driver behavior)

## Exceptions

This library wraps driver exceptions into `sqlmapper`-specific exceptions.

- `MappingError`
- `DriverWarning`
- `DriverError`
- `DriverInterfaceError`
- `DriverDatabaseError`
- `DriverDataError`
- `DriverOperationalError`
- `DriverIntegrityError`
- `DriverInternalError`
- `DriverProgrammingError`
- `DriverNotSupportedError`

## More Documents

Developer Guide: [DEVELOPMENT.md](DEVELOPMENT.md)  
TODO: [TODO.md](TODO.md)

## License

See [LICENSE](LICENSE).

## Distribution

PyPI: https://pypi.org/project/PythonSQLMapper/  
GitHub: https://github.com/marvelph/PythonSQLMapper

## Contact

Please use GitHub Issues for bug reports and feature requests.  
https://github.com/marvelph/PythonSQLMapper/issues  
Email: marvel@programmershigh.org
