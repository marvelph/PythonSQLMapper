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

    def __init__(self, database, user, password, host='localhost', port=3306):
        self.driver_class = MySQLdb
        self.cursor_class = MySQLdb.cursors.DictCursor
        self.error_class = MySQLdb.Error

        try:
            self.connection = self.driver_class.connect(host=host, port=port, user=user, passwd=password, db=database, charset='utf8')
        except self.error_class as error:
            raise DriverError(cause=error)

    # TODO: Support context manager
    def close(self):
        try:
            self.connection.close()
        except self.error_class as error:
            raise DriverError(cause=error)

    def select_one(self, sql, parameter=None, result_type=Result):
        try:
            cursor = self.connection.cursor(self.cursor_class);
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
        except self.error_class as error:
            raise DriverError(cause=error)

    def select_all(self, sql, parameter=None, result_type=Result):
        try:
            # TODO: Support generator
            cursor = self.connection.cursor(self.cursor_class);
            try:
                results = []
                cursor.execute(*self.__map_parameter(sql, parameter))
                for row in cursor.fetchall():
                    results.append(self.__create_result(row=row, result_type=result_type))
                return results
            finally:
                cursor.close()
        except self.error_class as error:
            raise DriverError(cause=error)

    def insert(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.cursor_class);
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.lastrowid
            finally:
                cursor.close()
        except self.error_class as error:
            raise DriverError(cause=error)

    def update(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.cursor_class);
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.error_class as error:
            raise DriverError(cause=error)

    def delete(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.cursor_class);
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
                return cursor.rowcount
            finally:
                cursor.close()
        except self.error_class as error:
            raise DriverError(cause=error)

    def execute(self, sql, parameter=None):
        try:
            cursor = self.connection.cursor(self.cursor_class);
            try:
                cursor.execute(*self.__map_parameter(sql, parameter))
            finally:
                cursor.close()
        except self.error_class as error:
            raise DriverError(cause=error)

    def commit(self):
        try:
            self.connection.commit();
        except self.error_class as error:
            raise DriverError(cause=error)

    def rollback(self):
        try:
            self.connection.rollback();
        except self.error_class as error:
            raise DriverError(cause=error)

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
