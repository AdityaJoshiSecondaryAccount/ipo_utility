import sqlite3
import rotki_pysqlcipher3 as sqlcipher
from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper

class DatabaseWrapper(SQLiteDatabaseWrapper):
    def get_connection_params(self):
        params = super().get_connection_params()
        # SQLCipher key
        params['factory'] = sqlcipher.Connection
        return params

    def get_new_connection(self, conn_params):
        conn = super().get_new_connection(conn_params)
        conn.execute("PRAGMA key='DbDefaultKey_1234567890';")
        return conn
