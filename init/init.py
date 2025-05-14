import os
from google.cloud.sql.connector import Connector
import pymysql


def get_db():
    connection = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pymysql",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def initialize_database():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            hashed_pass VARCHAR(100),
        )
    """)

    # cur.execute("""
    #     CREATE TABLE IF NOT EXISTS photos (
    #         id INT AUTO_INCREMENT PRIMARY KEY,
    #         user_id INT,
    #         url VARCHAR(255),
    #         uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         FOREIGN KEY (user_id) REFERENCES users(id)
    #     )
    # """)

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    initialize_database()