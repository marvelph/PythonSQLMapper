# PythonSQLMapper

PythonSQLMapper は、SQL の実行結果を Python オブジェクトへマッピングする小さなライブラリです。  
[iBATIS](https://ibatis.apache.org) に近い思想で、シンプルに使えることを重視しています。

- 対応DB: MySQL / PostgreSQL / SQLite
- Python: 3.5 以上

もともと iOS / macOS 向けの [CocoaSQLMapper](https://github.com/marvelph/CocoaSQLMapper) を Python 向けに再実装したものです。

## インストール

```bash
pip install PythonSQLMapper
```

## 基本の使い方

### 1. Mapper を作成する

`Mapper(driver, **connect_params)` に DB-API 互換ドライバと接続パラメータを渡します。

```python
import sqlite3
from sqlmapper import Mapper

mapper = Mapper(sqlite3, database="sample.db")
```

`with` を使わない場合は、処理の最後で `close()` を呼んで接続を明示的に閉じてください。

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

`with` 文も使えます。

```python
import sqlite3
from sqlmapper import Mapper

with Mapper(sqlite3, database="sample.db") as mapper:
    user = mapper.select_one(
        "SELECT id, name FROM users WHERE id = :id",
        {"id": 1},
    )
```

### 2. 名前付きバインド変数を使う

SQL では `:name` 形式のプレースホルダを使います。  
パラメータは `dict` または属性を持つオブジェクトで渡せます。  
実務では、検索条件は結果モデルと分けて `dataclass` で定義すると扱いやすくなります。

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
使い捨てなら `dict`、検索条件を再利用するなら `dataclass`、という使い分けがおすすめです。

### 3. 結果を受け取る

- `result_type` 指定時: 指定クラスのインスタンスへマッピングされる  
  (SQL の列名に対応する属性がクラス側に存在しないと `MappingError`)
- `result_type` 未指定時: 動的オブジェクト (`sqlmapper.Result`) が返る
- 入力パラメータ用クラスと結果クラスは同一でも別々でも構いません
- `result_type` は内部で `result_type()` として生成されるため、無引数で初期化できる必要があります

基本は `result_type` を指定して、列名と属性名の整合性をチェックしながら使うことを推奨します。JOIN や集計などで都度専用クラスを作るのが過剰な場合に限り、`result_type` 無指定の動的オブジェクト受け取りを使うと便利です。

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

同名カラムの解決は SQL 側で `AS` を使って行い、その別名をマッピング先の属性名として扱います。  
動的オブジェクトなら `row.user_id` のように参照でき、`result_type` を使う場合は同じ名前の属性をクラス側に用意します。

### 4. 追加 (`insert`) の `lastrowid` をモデルIDに使う

`insert` でも、`dict` だけでなくモデルクラスのインスタンスをそのまま渡せます。  
戻り値は `lastrowid`（ドライバ依存）なので、モデルの `id` として利用できます。

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

### 5. 更新 (`update`) の `rowcount` で楽観的ロックを判定する

`update` の戻り値は更新行数（`rowcount`）です。  
想定どおり 1 行更新されたかを確認できるため、楽観的ロック（`updated_at` や `version` を `WHERE` 条件に含める方式）の成否判定に利用できます。

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
    raise RuntimeError("競合により更新できませんでした。")

mapper.commit()
```

### 6. 削除 (`delete`) で条件を満たす場合だけ削除する

`delete` の戻り値は削除行数（`rowcount`）です。  
業務条件（例: `used_flag = 0` のときだけ削除）を `WHERE` に含めると、安全に削除可否を判定できます。

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
    raise RuntimeError("使用済みのため削除できない、または対象が存在しません。")

mapper.commit()
```

### 7. 特殊なSQLは `execute` で実行する

DDL（`ALTER TABLE` など）や、`insert` / `update` / `delete` / `select` に当てはまらない SQL は `execute` を使います。  
`execute` 自体は戻り値を持たないため、必要に応じて `commit()` を呼びます。

```python
mapper.execute(
    "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL"
)
mapper.commit()
```

### 8. トランザクションを制御する

autocommit を無効化した接続では、`Mapper` の生成（接続開始）後に行った更新は `commit()` するまで未確定です。  
書き込みをアトミックにしたい場合は、複数の更新をまとめて実行し、最後に `commit()` で確定します。  
`commit()` はトランザクションの区切りとして何度でも呼べるため、同一接続内で複数トランザクションを順に実行できます。  
途中で例外が発生して `commit()` 前に `with` ブロックを抜けた場合は未確定のため、ドライバ実装に従ってロールバックされます。

- `with` を使う場合: 例外で抜けると未確定更新はロールバックされます
- `Mapper` を使い回す場合: 失敗時は `rollback()` を明示して次処理へ未確定状態を持ち越さないようにします

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
# mapper: 事前に作成して使い回している Mapper インスタンス
# jobs: 処理対象ジョブの iterable
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
        mapper.rollback()  # 使い回し接続を次処理の前にクリーン化
        continue
```

## API

### `select_one(sql, parameter=None, result_type=None)`

- 1件取得
- 0件なら `None`
- 2件以上なら `MappingError`

### `select_all(sql, parameter=None, result_type=None, array_size=1, buffered=True)`

- 複数件取得 (`yield` で順次返却)
- `array_size` は `fetchmany` の件数
- `buffered` はドライバに応じてバッファ付き/なしカーソルを使い分け

```python
for user in mapper.select_all(
    "SELECT id, name FROM users WHERE status = :status",
    {"status": "active"},
    array_size=100,
):
    print(user.id, user.name)
```

### `insert(sql, parameter=None)`

- INSERT 実行
- `lastrowid` を返す

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

`lastrowid` の意味は DB/ドライバ実装に依存します。  
厳密なキー取得が必要な場合は、各DBの推奨手段（例: PostgreSQL の `RETURNING`）を利用してください。

### `update(sql, parameter=None)`

- UPDATE 実行
- 更新件数 (`rowcount`) を返す

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

- DELETE 実行
- 削除件数 (`rowcount`) を返す

```python
deleted = mapper.delete(
    "DELETE FROM users WHERE id = :id AND used_flag = 0",
    {"id": 1},
)
```

### `execute(sql, parameter=None)`

- 任意 SQL 実行
- 戻り値なし

```python
mapper.execute(
    "ALTER TABLE users ADD COLUMN profile TEXT"
)
mapper.commit()
```

### `commit()` / `rollback()` / `close()`

- トランザクション制御、接続クローズ

## 例外

このライブラリはドライバ例外を `sqlmapper` 独自例外へラップして送出します。

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

## ライセンス

MIT License
