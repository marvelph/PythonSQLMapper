#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  SQLMapper.py
#  PythonSQLMapper
#
#  Copyright 2013 Kenji Nishishiro. All rights reserved.
#  Written by Kenji Nishishiro <marvel@programmershigh.org>.
#

import re


class Error(Exception):

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return str(self.message)


class DriverWarning(Error):

    def __init__(self, cause):
        self.cause = cause

    def __str__(self):
        return str(self.cause)


class DriverError(Error):

    def __init__(self, cause):
        self.cause = cause

    def __str__(self):
        return str(self.cause)


class Result(object):
    pass


class Mapper(object):

    def __init__(self, driver, **kwargs):
        try:
            self.driver = driver
            if driver.__name__ == 'MySQLdb':
                import MySQLdb.cursors
                self.__cursor_class = MySQLdb.cursors.DictCursor
                self.__place_holder = '%s'
            elif driver.__name__ == 'oursql':
                self.__cursor_class = driver.DictCursor
                self.__place_holder = '?'
            else:
                raise Error(message='Unsupported driver.')

            self.connection = self.driver.connect(**kwargs)
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def close(self):
        try:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def select_one(self, sql, parameter=None, result_type=Result):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                if cursor.rowcount == 0:
                    return None
                elif cursor.rowcount == 1:
                    return self.__create_result(row=cursor.fetchone(), result_type=result_type)
                else:
                    raise Error(message='Multiple result was obtained.')
            finally:
                cursor.close()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def select_all(self, sql, parameter=None, result_type=Result, array_size=1):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                rows = cursor.fetchmany(array_size)
                while rows:
                    for row in rows:
                        yield self.__create_result(row=row, result_type=result_type)
                    rows = cursor.fetchmany(array_size)
            finally:
                cursor.close()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def insert(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.lastrowid
            finally:
                cursor.close()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def update(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def delete(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def execute(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
            finally:
                cursor.close()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def commit(self):
        try:
            self.connection.commit()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def rollback(self):
        try:
            self.connection.rollback()
        except self.driver.Warning as error:
            raise DriverWarning(cause=error)
        except self.driver.Error as error:
            raise DriverError(cause=error)

    def __map_parameter(self, sql, parameter):
        represented_sql = ''
        parameters = ()
        start = 0
        for match in re.finditer(':[a-zA-Z_][a-zA-Z0-9_]+', sql):
            # TODO: Support paramstyle
            represented_sql += sql[start:match.start()] + self.__place_holder
            start = match.end()
            parameters += (self.__get_variable(parameter, sql[match.start() + 1:match.end()]),)
        represented_sql += sql[start:]
        return represented_sql, parameters

    def __get_variable(self, parameter, name):
        try:
            if isinstance(parameter, dict):
                return parameter[name]
            else:
                return getattr(parameter, name)
        except (KeyError, AttributeError):
            raise Error(message='Bind variable not found.')

    def __create_result(self, row, result_type):
        if result_type == Result:
            result = Result()
            for name in row:
                setattr(result, name, row[name])
            return result
        else:
            try:
                result = result_type(**row)
                return result
            except TypeError:
                raise Error(message='Constructor of the result type do not match.')
