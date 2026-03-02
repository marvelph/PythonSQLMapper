#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  sqlmapper.py
#  PythonSQLMapper
#
#  Copyright 2013-2023 Kenji Nishishiro. All rights reserved.
#  Written by Kenji Nishishiro <marvel@programmershigh.org>.
#

import re


class MappingError(Exception):
    pass


class DriverWarning(MappingError):
    pass


class DriverError(MappingError):
    pass


class DriverInterfaceError(DriverError):
    pass


class DriverDatabaseError(DriverError):
    pass


class DriverDataError(DriverDatabaseError):
    pass


class DriverOperationalError(DriverDatabaseError):
    pass


class DriverIntegrityError(DriverDatabaseError):
    pass


class DriverInternalError(DriverDatabaseError):
    pass


class DriverProgrammingError(DriverDatabaseError):
    pass


class DriverNotSupportedError(DriverDatabaseError):
    pass


class Result(object):
    pass


class Mapper(object):
    def __init__(self, driver, **params):
        self.connection = None
        try:
            self.driver = driver
            if driver.__name__ == "sqlite3":
                self.__cursor_params = {}
                self.__buffered_cursor_params = self.__cursor_params
                self.__place_holder = "?"
            elif driver.__name__ == "mysql.connector":
                self.__cursor_params = {"dictionary": True}
                self.__buffered_cursor_params = {"dictionary": True, "buffered": True}
                self.__place_holder = "%s"
            elif driver.__name__ == "MySQLdb":
                import MySQLdb.cursors

                self.__cursor_params = {"cursorclass": MySQLdb.cursors.SSDictCursor}
                self.__buffered_cursor_params = {"cursorclass": MySQLdb.cursors.DictCursor}
                self.__place_holder = "%s"
            elif driver.__name__ == "pymysql":
                import pymysql.cursors

                self.__cursor_params = {"cursor": pymysql.cursors.SSDictCursor}
                self.__buffered_cursor_params = {"cursor": pymysql.cursors.DictCursor}
                self.__place_holder = "%s"
            elif driver.__name__ == "psycopg2":
                import psycopg2.extras

                self.__cursor_params = {"cursor_factory": psycopg2.extras.RealDictCursor}
                self.__buffered_cursor_params = self.__cursor_params
                self.__place_holder = "%s"
            else:
                raise MappingError(
                    f"Unsupported driver '{driver.__name__}'. Supported drivers: sqlite3, mysql.connector, "
                    "MySQLdb, pymysql, psycopg2."
                )

            self.connection = self.driver.connect(**params)
            if driver.__name__ == "sqlite3":
                self.connection.row_factory = self.__sqlite3_dict_factory
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def close(self):
        try:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def select_one(self, sql, parameter=None, result_type=None):
        try:
            cursor = self.connection.cursor(**self.__cursor_params)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                rows = cursor.fetchmany(2)
                if len(rows) == 0:
                    return None
                elif len(rows) == 1:
                    return self.__create_result(row=rows[0], result_type=result_type)
                else:
                    raise MappingError("Expected exactly one row, but multiple rows were returned.")
            finally:
                cursor.close()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def select_all(self, sql, parameter=None, result_type=None, array_size=1, buffered=True):
        try:
            if buffered:
                cursor = self.connection.cursor(**self.__buffered_cursor_params)
            else:
                cursor = self.connection.cursor(**self.__cursor_params)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                rows = cursor.fetchmany(array_size)
                while rows:
                    for row in rows:
                        yield self.__create_result(row=row, result_type=result_type)
                    rows = cursor.fetchmany(array_size)
            finally:
                cursor.close()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def insert(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(**self.__cursor_params)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.lastrowid
            finally:
                cursor.close()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def update(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(**self.__cursor_params)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def delete(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(**self.__cursor_params)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def execute(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(**self.__cursor_params)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
            finally:
                cursor.close()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def commit(self):
        try:
            self.connection.commit()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def rollback(self):
        try:
            self.connection.rollback()
        except self.driver.NotSupportedError as error:
            raise DriverNotSupportedError(*error.args) from error
        except self.driver.ProgrammingError as error:
            raise DriverProgrammingError(*error.args) from error
        except self.driver.InternalError as error:
            raise DriverInternalError(*error.args) from error
        except self.driver.IntegrityError as error:
            raise DriverIntegrityError(*error.args) from error
        except self.driver.OperationalError as error:
            raise DriverOperationalError(*error.args) from error
        except self.driver.DataError as error:
            raise DriverDataError(*error.args) from error
        except self.driver.DatabaseError as error:
            raise DriverDatabaseError(*error.args) from error
        except self.driver.InterfaceError as error:
            raise DriverInterfaceError(*error.args) from error
        except self.driver.Error as error:
            raise DriverError(*error.args) from error
        except self.driver.Warning as error:
            raise DriverWarning(*error.args) from error

    def __map_parameter(self, sql, parameter):
        represented_sql = ""
        parameters = ()
        start = 0
        for match in re.finditer(":[a-zA-Z_][a-zA-Z0-9_]+", sql):
            # TODO: Support paramstyle
            represented_sql += sql[start : match.start()] + self.__place_holder
            start = match.end()
            parameters += (self.__get_variable(parameter, sql[match.start() + 1 : match.end()]),)
        represented_sql += sql[start:]
        return represented_sql, parameters

    @staticmethod
    def __sqlite3_dict_factory(cursor, row):
        fields = [column[0] for column in cursor.description]
        return {key: value for key, value in zip(fields, row)}

    @staticmethod
    def __get_variable(parameter, name):
        if isinstance(parameter, dict):
            try:
                return parameter[name]
            except KeyError:
                raise MappingError(
                    f"Bind variable '{name}' was not found in dict parameter. Available keys: {sorted(parameter.keys())}"
                )
        else:
            try:
                return getattr(parameter, name)
            except AttributeError:
                raise MappingError(
                    f"Bind variable '{name}' was not found in parameter object of type '{type(parameter).__name__}'."
                )

    @staticmethod
    def __create_result(row, result_type):
        if result_type is None:
            result = Result()
            for name in row:
                setattr(result, name, row[name])
            return result
        else:
            try:
                result = result_type()
            except TypeError:
                raise MappingError(f"Result type '{result_type}' must be instantiable without arguments.")
            for name in row:
                if hasattr(result, name):
                    setattr(result, name, row[name])
                else:
                    raise MappingError(f"Attribute '{name}' was not found in result_type '{result_type.__name__}'.")
            return result
