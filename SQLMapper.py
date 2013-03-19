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

import MySQLdb
from MySQLdb import cursors


class Error(Exception):

    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return str(self.message)


class DriverError(Error):

    def __init__(self, cause=None):
        self.cause = cause

    def __str__(self):
        return str(self.cause)


class Result(object):
    pass


class Mapper(object):

    def __init__(self, database, user, password, host='localhost', port=3306, character_set='utf8'):
        self.__driver_class = MySQLdb
        self.__cursor_class = MySQLdb.cursors.DictCursor
        self.__error_class = MySQLdb.Error

        try:
            self.connection = self.__driver_class.connect(host=host, port=port, user=user, passwd=password, db=database,
                                                          charset=character_set)
        except self.__error_class as error:
            raise DriverError(cause=error)

    def close(self):
        try:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
        except self.__error_class as exc:
            raise DriverError(cause=exc)

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
        except self.__error_class as exc:
            raise DriverError(cause=exc)

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
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def insert(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.lastrowid
            finally:
                cursor.close()
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def update(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def delete(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def execute(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.__cursor_class)
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
            finally:
                cursor.close()
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def commit(self):
        try:
            self.connection.commit()
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def rollback(self):
        try:
            self.connection.rollback()
        except self.__error_class as exc:
            raise DriverError(cause=exc)

    def __map_parameter(self, sql, parameter):
        represented_sql = ''
        parameters = ()
        start = 0
        for match in re.finditer(':[a-zA-Z_][a-zA-Z0-9_]+', sql):
            # TODO: Support paramstyle
            represented_sql += sql[start:match.start()] + '%s'
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
