
from django.db.backends.sqlite3 import base

try:
    from pysqlcipher3 import dbapi2 as Database
except ImportError as e1:
    try:
        import sqlcipher3 as Database
    except ImportError as e2:
        try:
            from sqlcipher3 import dbapi2 as Database
        except ImportError as e3:
            raise ImportError(f"SQLCipher3 is not installed or failed to load. (pysqlcipher3: {e1}, sqlcipher3: {e2}, sqlcipher3.dbapi2: {e3})")

class SQLCipherCursorWrapper(Database.Cursor):
    def execute(self, query, params=None):
        if params is None:
            return super().execute(query)
        query = self.convert_query(query)
        return super().execute(query, params)

    def executemany(self, query, params=None):
        query = self.convert_query(query)
        return super().executemany(query, params)

    def convert_query(self, query):
        return query.replace('%s', '?')

# Register adapters for pysqlcipher3 to handle Django types
import datetime
import decimal

Database.register_adapter(decimal.Decimal, str)
Database.register_adapter(datetime.date, lambda d: d.isoformat())
Database.register_adapter(datetime.time, lambda t: t.isoformat())
Database.register_adapter(datetime.datetime, lambda dt: dt.isoformat(" "))

from django.db.backends.sqlite3 import features

class DatabaseFeatures(features.DatabaseFeatures):
    @property
    def max_query_params(self):
        return 999

class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.features.can_return_columns_from_insert = False

    def get_new_connection(self, conn_params):
        conn = Database.connect(**conn_params)
        
        password = self.settings_dict.get('PASSWORD')
        if password:
            # For SQLCipher, the key must be set before any other operation.
            # Using standard PRAGMA syntax.
            conn.execute(f"PRAGMA key = '{password}'")
            
        return conn

    def create_cursor(self, name=None):
        return self.connection.cursor(factory=SQLCipherCursorWrapper)


