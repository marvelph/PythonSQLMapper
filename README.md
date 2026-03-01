# PythonSQLMapper

PythonSQLMapper is a small library that maps SQL results to Python objects.  
It is inspired by [iBATIS](https://ibatis.apache.org) and focuses on simplicity.

- Supported databases: MySQL / PostgreSQL / SQLite
- Python: 3.5+

It is a Python reimplementation of [CocoaSQLMapper](https://github.com/marvelph/CocoaSQLMapper), originally built for iOS/macOS.

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

If you do not use `with`, call `close()` explicitly at the end.

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

You can also use a `with` statement.

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
Parameters can be passed as either a `dict` or an object with attributes.  
In practice, it is often easier to define query conditions as a separate `dataclass` from your result model.

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

A good rule of thumb: use `dict` for one-off use, and `dataclass` for reusable query conditions.

### 3. Receive Results

- When `result_type` is specified: rows are mapped to instances of that class  
  (raises `MappingError` if a SQL column has no matching attribute)
- When `result_type` is omitted: returns a dynamic object (`sqlmapper.Result`)
- Input parameter class and output class may be the same or different
- `result_type` is instantiated internally via `result_type()`, so it must support no-arg initialization

As a default, specifying `result_type` is recommended to keep column/attribute mapping checks. Use dynamic objects only when defining dedicated classes is excessive (for example, ad-hoc JOIN or aggregation queries).

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

Handle duplicate column names in SQL with `AS`, then map those aliases as attribute names.  
For dynamic objects, access `row.user_id`, etc. For `result_type`, define attributes with the same names.

### 4. Use `insert` `lastrowid` as Model ID

`insert` accepts model instances as input parameters, not only `dict`.  
Its return value is `lastrowid` (driver-dependent), which you can use as your model `id`.

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

### 5. Use `update` `rowcount` for Optimistic Lock Checks

`update` returns the number of updated rows (`rowcount`).  
You can use this to detect optimistic lock failures (for example, by including `updated_at` or `version` in `WHERE`).

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

### 6. Delete Only When Conditions Match

`delete` returns the number of deleted rows (`rowcount`).  
By putting business conditions in `WHERE` (for example, delete only when `used_flag = 0`), you can safely decide whether deletion is allowed.

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
    raise RuntimeError("Cannot delete: already used, or target does not exist.")

mapper.commit()
```

### 7. Run Special SQL with `execute`

Use `execute` for DDL (`ALTER TABLE`, etc.) or SQL that does not fit `insert` / `update` / `delete` / `select`.  
`execute` does not return a value, so call `commit()` when needed.

```python
mapper.execute(
    "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL"
)
mapper.commit()
```

### 8. Control Transactions

With autocommit disabled, updates after creating `Mapper` (opening a connection) remain uncommitted until `commit()`.  
For atomic writes, execute multiple updates together and commit at the end.  
You can call `commit()` multiple times as transaction boundaries, running multiple transactions on one connection.  
If an exception exits a `with` block before `commit()`, pending changes are rolled back according to the driver implementation.

- With `with`: uncommitted updates are rolled back when exiting by exception (`Mapper` does not call `rollback()` explicitly; it relies on driver behavior at connection close)
- Reusing `Mapper`: call `rollback()` explicitly on failure so pending state is not carried into the next operation

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
# mapper: a pre-created, reused Mapper instance
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
        mapper.rollback()  # clean reused connection state before next job
        continue
```

## API

### `select_one(sql, parameter=None, result_type=None)`

- Fetches one row
- Returns `None` when no rows are found
- Raises `MappingError` when multiple rows are returned

### `select_all(sql, parameter=None, result_type=None, array_size=1, buffered=True)`

- Fetches multiple rows as a generator
- `array_size` is the chunk size for `fetchmany`
- When `buffered=True`, it uses a cursor that buffers result sets, if provided by the driver
- When `buffered=False`, it uses a cursor that does not buffer result sets, if provided by the driver
- Some drivers do not offer cursor alternatives, so both modes may behave the same

```python
for user in mapper.select_all(
    "SELECT id, name FROM users WHERE status = :status",
    {"status": "active"},
    array_size=100,
):
    print(user.id, user.name)
```

### `insert(sql, parameter=None)`

- Executes INSERT
- Returns `lastrowid`

```python
class NewUser:
    def __init__(self, name, status):
        self.name = name
        self.status = status

new_id = mapper.insert(
    "INSERT INTO users (name, status) VALUES (:name, :status)",
    NewUser(name="Alice", status="active"),
)
```

The meaning of `lastrowid` depends on the DB/driver implementation.  
If you need strict key retrieval semantics, use each DB's recommended approach (for example, `RETURNING` in PostgreSQL).

### `update(sql, parameter=None)`

- Executes UPDATE
- Returns number of updated rows (`rowcount`)

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

- Executes DELETE
- Returns number of deleted rows (`rowcount`)

```python
deleted = mapper.delete(
    "DELETE FROM users WHERE id = :id AND used_flag = 0",
    {"id": 1},
)
```

### `execute(sql, parameter=None)`

- Executes arbitrary SQL
- No return value

```python
mapper.execute(
    "ALTER TABLE users ADD COLUMN profile TEXT"
)
mapper.commit()
```

### `commit()` / `rollback()` / `close()`

- Transaction control and connection close

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

## License

MIT License
