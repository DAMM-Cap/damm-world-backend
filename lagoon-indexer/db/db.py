from typing import List
import os
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd

class Database:
    def __init__(self, host, port, db_name, user, password):
        self.connection = psycopg2.connect(
            host=host,
            port=port,
            database=db_name,
            user=user,
            password=password
        )

    def closeConnection(self):
        if self.connection is not None:
            self.connection.close()

    def queryResponse(self, query, params=None, raw=False, commit=False):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
        except Exception as e:
            print(e)
            self.connection.rollback()
            return
        raw_response = cursor.fetchall()

        if raw:
            cursor.close()
            return raw_response

        col_names = [d[0] for d in cursor.description]
        result = []
        for row in raw_response:
            row_dict = {}
            for i, col_name in enumerate(col_names):
                row_dict[col_name] = row[i]
            result.append(row_dict)

        if commit:
            self.connection.commit()
        cursor.close()
        return result

    def frameResponse(self, query, params=None):
        return pd.DataFrame(self.queryResponse(query, params))

    def execute(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
        except Exception as e:
            print(e)
            self.connection.rollback()
            return False
        self.connection.commit()
        cursor.close()
        return True

    def executeMultiple(self, query_list: List[str]) -> bool:
        with self.connection.cursor() as cursor:
            for query in query_list:
                try:
                    cursor.execute(query)
                except Exception as e:
                    print(e)
                    self.connection.rollback()
                    return False
            self.connection.commit()
            return True

    def insertDf(self, df: pd.DataFrame, table_name: str):
        if len(df) == 0:
            return
        with self.connection.cursor() as cursor:
            insert_query = f"""INSERT INTO "{table_name}" ({','.join(df.columns)}) VALUES %s"""
            values = df.to_records(index=False).tolist()
            try:
                execute_values(cursor, insert_query, values)
                self.connection.commit()
                return True
            except Exception as e:
                print(e)
                self.connection.rollback()
                return False

    def getColumns(self, table):
        col_query = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table}'
        """
        return self.queryResponse(col_query)

    def getDf(self, table_name):
        cols = [c[0] for c in self.getColumns(table_name)]
        query = f"""
            select {','.join(cols)}
            from "{table_name}"
        """
        response = self.queryResponse(query)
        return pd.DataFrame(response, columns=cols)

    def getTables(self):
        query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """
        return [row[0] for row in self.queryResponse(query, raw=True)]

    def getTableInfo(self, table_name):
        query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = '{table_name}'
        """
        return self.queryResponse(query)

    def describe(self):
        tables = self.getTables()
        response = {}
        for table in tables:
            response[table] = self.getTableInfo(table)
        return response

def getEnvDb(db_name: str = '') -> Database:
    db_name = db_name if db_name != '' else os.getenv('DB_NAME')
    return Database(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        db_name=db_name,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
