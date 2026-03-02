# Developer Guide

Use `venv` for the Python virtual environment.  
Manage required environment variables in a `.env` file.

## Python Environment

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## Install Test Drivers

```bash
source .venv/bin/activate
python -m pip install mysql-connector-python pymysql mysqlclient psycopg2
```

`mysqlclient` and `psycopg2` may require additional native dependencies depending on your environment.

## MySQL Test Database Setup

Open a MySQL shell with an administrative user and run the following:

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

## PostgreSQL Test Database Setup

Open `psql` with an administrative user and run the following:

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

## `.env` Configuration

Create `.env` in the project root and set the following values:

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

## Run Tests

```bash
set -a && source .env && set +a
source .venv/bin/activate
```

SQLite3:

```bash
python -m unittest -v tests/test_sqlmapper_sqlite3.py
```

MySQL (`mysql.connector`):

```bash
python -m unittest -v tests/test_sqlmapper_mysql.py
```

MySQL (`pymysql`):

```bash
python -m unittest -v tests/test_sqlmapper_pymysql.py
```

MySQL (`MySQLdb` / `mysqlclient`):

```bash
python -m unittest -v tests/test_sqlmapper_mysqldb.py
```

PostgreSQL (`psycopg2`):

```bash
python -m unittest -v tests/test_sqlmapper_psycopg2.py
```
