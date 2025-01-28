import psycopg2
from psycopg2 import sql

class PostgresManager:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def connect_with_url(self, url):
        self.connection = psycopg2.connect(url)
        self.cursor = self.connection.cursor()

    def upsert(self, table_name, data_dict):
        columns = data_dict.keys()
        values = [data_dict[column] for column in columns]
        insert_stmt = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values}) "
                              "ON CONFLICT (id) DO UPDATE SET {updates}")
        updates = [sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column)) for column in columns]
        query = insert_stmt.format(
            table=sql.Identifier(table_name),
            columns=sql.SQL(', ').join(map(sql.Identifier, columns)),
            values=sql.SQL(', ').join(sql.Placeholder() * len(values)),
            updates=sql.SQL(', ').join(updates)
        )
        self.cursor.execute(query, values)
        self.connection.commit()

    def delete(self, table_name, id):
        self.cursor.execute("DELETE FROM {} WHERE id = %s".format(table_name), (id,))
        self.connection.commit()

    def get(self, table_name, id):
        self.cursor.execute("SELECT * FROM {} WHERE id = %s".format(table_name), (id,))
        return self.cursor.fetchone()

    def get_all(self, table_name):
        self.cursor.execute("SELECT * FROM {}".format(table_name))
        return self.cursor.fetchall()

    def run_sql(self, sql):
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_table_definition(self, table_name):
        self.cursor.execute("SELECT pg_dump('--table={}', '--no-owner', '--no-comments', '--no-privileges', '-w', '-s', '{}')".format(table_name, self.connection.dsn))
        return self.cursor.fetchone()[0]

    def get_all_table_names(self):
        self.cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        return [row[0] for row in self.cursor.fetchall()]

    def get_table_definition_for_prompt(self):
        table_names = self.get_all_table_names()
        table_definitions = []
        for table in table_names:
            table_definitions.append(self.get_table_definition(table))
        return "\n".join(table_definitions)