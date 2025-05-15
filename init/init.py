import os
from google.cloud.sql.connector import Connector
import pymysql


INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")
CLOUD_SQL_PUBLIC_IP = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")                # Your DB username
DB_PASSWORD = os.getenv("DB_PASSWORD")          # Your DB password
DB_NAME = os.getenv("DB_NAME")    # Make sure this matches your DB name exactly 
connector = Connector()

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
            password_hash VARCHAR(100)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            filename VARCHAR(255),
            title VARCHAR(50),
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    initialize_database()