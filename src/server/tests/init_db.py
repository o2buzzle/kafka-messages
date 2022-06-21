import configparser
import sqlite3

config = configparser.ConfigParser()
config.read("config.ini")
USERS_DATABASE = config["Server"]["USERS_DATABASE"]

if __name__ == "__main__":
    # initialize database
    db = sqlite3.connect(USERS_DATABASE)
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT, 
            password TEXT, 
            status BOOLEAN DEFAULT true, 
            PRIMARY KEY (username))
            """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            username TEXT,
            session_id TEXT,
            PRIMARY KEY (username, session_id))
            """
    )
    db.commit()
