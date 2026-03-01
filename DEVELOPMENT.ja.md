# 開発者向けガイド

Python の仮想環境には `venv` を使用して開発します。  
必要な環境変数は `.env` ファイルで管理します。

## Python 環境

```bash
python3.8 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## テスト用ドライバのインストール

```bash
source .venv/bin/activate
python -m pip install mysql-connector-python pymysql mysqlclient psycopg2
```

`mysqlclient` と `psycopg2` は、環境によって追加のネイティブ依存ライブラリが必要になる場合があります。

## MySQL テスト用データベースのセットアップ

管理者権限のあるユーザで MySQL シェルに入り、以下を実行します。

```bash
mysql
```

```sql
CREATE DATABASE sqlmapper
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER 'sqlmapper'@'localhost' IDENTIFIED BY 'sqlmapper';
GRANT ALL ON sqlmapper.* TO 'sqlmapper'@'localhost';
```

## PostgreSQL テスト用データベースのセットアップ

管理者権限のあるユーザで `psql` に入り、以下を実行します。

```bash
psql
```

```sql
CREATE DATABASE sqlmapper
  TEMPLATE template0
  ENCODING 'UTF8'
  LC_COLLATE 'C'
  LC_CTYPE 'C';

CREATE USER sqlmapper WITH PASSWORD 'sqlmapper';
GRANT ALL PRIVILEGES ON DATABASE sqlmapper TO sqlmapper;
\c sqlmapper
GRANT ALL ON SCHEMA public TO sqlmapper;
```

## `.env` の設定

プロジェクトルートに `.env` を作成し、以下を設定します。

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=sqlmapper
MYSQL_PASSWORD=sqlmapper
MYSQL_DATABASE=sqlmapper

PGHOST=localhost
PGPORT=5432
PGUSER=sqlmapper
PGPASSWORD=sqlmapper
PGDATABASE=sqlmapper
```

## テストの実行

```bash
set -a && source .env && set +a
source .venv/bin/activate
```

SQLite3:

```bash
python -m unittest -v test_sqlmapper_sqlite3.py
```

MySQL (`mysql.connector`):

```bash
python -m unittest -v test_sqlmapper_mysql.py
```

MySQL (`pymysql`):

```bash
python -m unittest -v test_sqlmapper_pymysql.py
```

MySQL (`MySQLdb` / `mysqlclient`):

```bash
python -m unittest -v test_sqlmapper_mysqldb.py
```

PostgreSQL (`psycopg2`):

```bash
python -m unittest -v test_sqlmapper_psycopg2.py
```
