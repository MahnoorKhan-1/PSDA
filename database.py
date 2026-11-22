
import sqlite3


def create_database():
    connection = sqlite3.connect("stocks.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            shares INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def get_stocks():
    connection = sqlite3.connect("stocks.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM stocks")
    stocks = cursor.fetchall()

    connection.close()
    return stocks


def save_stock(symbol, shares, price):
    connection = sqlite3.connect("stocks.db")
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO stocks (symbol, shares, price) VALUES (?, ?, ?)",
        (symbol, shares, price)
    )

    connection.commit()
    connection.close()



def update_stock(stock_id, shares, price):
    connection = sqlite3.connect("stocks.db")
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE stocks SET shares = ?, price = ? WHERE id = ?",
        (shares, price, stock_id)
    )

    connection.commit()
    connection.close()



def delete_stock(stock_id):
    connection = sqlite3.connect("stocks.db")
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM stocks WHERE id = ?",
        (stock_id,)
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print("Database created successfully!")

