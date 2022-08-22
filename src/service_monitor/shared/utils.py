import os

def construct_output(result, columns):
    return [{columns[i]: r[i] for i in range(len(columns))} for r in result]

def init_database(db):
    cursor = db.cursor()
    db_name = os.getenv('DB_NAME')
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.execute(f"""\
                CREATE TABLE IF NOT EXISTS {db_name}.urls (
                name varchar(20),
                url varchar(200),
                status ENUM('success', 'fail'),
                creation_date DATETIME,
                INDEX idx_entry (name, url)
            )""")
    cursor.close()

    