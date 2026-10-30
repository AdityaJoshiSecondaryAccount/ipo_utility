import pysqlcipher3.dbapi2 as Database
from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper


class DatabaseWrapper(SQLiteDatabaseWrapper):
    vendor = "sqlite"
    display_name = "SQLCipher"
    paramstyle = "qmark"   # ✅ THIS FIXES "%"

    def get_new_connection(self, conn_params):
        conn = Database.connect(conn_params["database"])
        cursor = conn.cursor()

        password = self.settings_dict.get("PASSWORD")
        if password:
            cursor.execute(f"PRAGMA key = '{password}';")

        # ✅ VERY IMPORTANT FOR MIGRATIONS
        cursor.execute("PRAGMA foreign_keys=OFF;")

        return conn

    def create_cursor(self, name=None):
        return self.connection.cursor()
