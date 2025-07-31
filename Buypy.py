#!/usr/bin/env python3

import mysql.connector
import configparser
import os
import subprocess
import datetime
import sys
from decimal import Decimal
from cryptography.fernet import Fernet

KEY = b"WZfl7FTRq7KuJ1-GVP5mGC7dkqK8AwylPKRiVPm9LXM="
cipher = Fernet(KEY)
CONFIG_FILE = "config.ini"

DB_NAME = "buypy"
DB_USER = "BUYDB_OPERATOR"
DB_PASS = "Lmxy20#a"
DB_HOST = "localhost"


def connect():
    return mysql.connector.connect(
        user=DB_USER, password=DB_PASS, host=DB_HOST, database=DB_NAME
    )


def login():
    print("\n== BuyPy login ==")
    email = input("Email: ").strip()
    pw = input("Password: ").strip()

    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id FROM operator
       WHERE email = %s
         AND password = LEFT(SHA2(%s, 256), 50)""",
            (email, pw),
        )
        row = cur.fetchone()
        if row:
            store_credentials(email, pw)
            print("Welcome operator.")
            return True
        print("Invalid credentials.")
        return False
    finally:
        cur.close()
        conn.close()


def store_credentials(user, pw):
    cfg = configparser.ConfigParser()
    cfg["CREDENTIALS"] = {
        "user": cipher.encrypt(user.encode()).decode(),
        "password": cipher.encrypt(pw.encode()).decode(),
    }
    with open(CONFIG_FILE, "w") as f:
        cfg.write(f)


def user_menu():
    while True:
        print("\n== Client menu ==")
        print("1  Search client")
        print("2  View client")
        print("3  Block / Unblock client")
        print("0  Back")
        c = input("> ").strip()
        if c == "1":
            search_client()
        elif c == "2":
            view_client()
        elif c == "3":
            toggle_client()
        elif c == "0":
            break


def search_client():
    term = input("ID or name fragment: ").strip()
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """select id, firstname, surname, email,
                  case when is_active is null or is_active=1 then 'Active' else 'Blocked' END
               from client
               where firstname like %s or surname like %s or id = %s""",
        (f"%{term}%", f"%{term}%", term if term.isdigit() else -1),
    )
    for r in cur.fetchall():
        print(f"{r[0]:<4} {r[1]} {r[2]} | {r[3]} | {r[4]}")
    cur.close()
    conn.close()


def view_client():
    cid = input("Client ID: ").strip()
    conn = connect()
    cur = conn.cursor()
    cur.execute("select * from client where id=%s", (cid,))
    row = cur.fetchone()
    if not row:
        print("Not found.")
    else:
        for col, val in zip([d[0] for d in cur.description], row):
            print(f"{col}: {val}")
    cur.close()
    conn.close()


def toggle_client():
    cid = input("Client ID: ").strip()
    val = 0 if input("Block (B) / Unblock (U): ").strip().upper() == "B" else 1
    conn = connect()
    cur = conn.cursor()
    cur.execute("update client set is_active=%s where id=%s", (val, cid))
    conn.commit()
    print("Updated." if cur.rowcount else "Client not found.")
    cur.close()
    conn.close()


def product_menu():
    while True:
        print("\n== Product menu ==")
        print("1  List products")
        print("2  Add book")
        print("3  Add electronic")
        print("0  Back")
        o = input("> ").strip()
        if o == "1":
            list_products()
        elif o == "2":
            add_book()
        elif o == "3":
            add_electronic()
        elif o == "0":
            break


def list_products():
    conn = connect()
    cur = conn.cursor()
    type_filter = input("Enter product type: ").strip()

    cur.execute(
        """select p.id, p.price, p.quantity,
                  case when b.product_id is not null then 'Book'
                       when e.product_id is not null then 'Electronic'
                       else 'Unknown' end as type,
                  p.score,
                  COALESCE(p.is_active,1)
               from product p
               left join book b ON b.product_id=p.id
               left join electronic e ON e.product_id=p.id"""
    )
    if type_filter:
        cur.execute(
            f"""select p.id, p.price, p.quantity,
                       case when b.product_id is not null then 'Book'
                            when e.product_id is not null then 'Electronic'
                            else 'Unknown' end as type,
                       p.score,
                       COALESCE(p.is_active,1)
                    from product p
                    left join book b ON b.product_id=p.id
                    left join electronic e ON e.product_id=p.id
                    where type = '{type_filter}'"""
        )

    print(f"{'ID':<8}{'Price':>10}{'Qty':>6}{'Type':>12}{'Score':>7}{'Active':>8}")
    for r in cur.fetchall():
        print(
            f"{r[0]:<8}{r[1]:>10.2f}{r[2]:>6}{r[3]:>12}{r[4]:>7}{('Yes' if r[5] else 'No'):>8}"
        )
    cur.close()
    conn.close()


def yn(msg):
    return input(msg + " [y/n]: ").lower().startswith("y")


def add_book():
    print("\n== Add book ==")
    params = [
        input("Product ID: ").strip(),
        int(input("Quantity: ")),
        str(input("Price: ")),
        float(input("VAT %: ")),
        int(input("Score 1-5: ")),
        (ip := input("Image path (optional): ").strip()) or None,
        int(yn("Active product?")),
        None if yn("Active product?") else input("Reason inactive: ").strip(),
        input("ISBN-13: ").strip(),
        input("Title: ").strip(),
        input("Genre: ").strip(),
        input("Publisher: ").strip(),
        input("Publication date YYYY-MM-DD: ").strip(),
    ]
    conn = connect()
    cur = conn.cursor()
    cur.callproc("sp_addbook", params)
    conn.commit()
    cur.close()
    conn.close()
    print("Book inserted.")


def add_electronic():
    print("\n== Add electronic ==")
    params = [
        input("Product ID: ").strip(),
        int(input("Quantity: ")),
        str(input("Price: ")),
        float(input("VAT %: ")),
        int(input("Score 1-5: ")),
        (ip := input("Image path (optional): ").strip()) or None,
        int(yn("Active product?")),
        None if yn("Active product?") else input("Reason inactive: ").strip(),
        input("Serial number: ").strip(),
        input("Brand: ").strip(),
        input("Model: ").strip(),
        input("Technical specs: ").strip(),
        input("Type: ").strip(),
    ]
    conn = connect()
    cur = conn.cursor()
    cur.callproc("sp_addelectronic", params)
    conn.commit()
    cur.close()
    conn.close()
    print("Electronic inserted.")


def create_order(cursor):
    try:
        client_id = int(input("Client ID: "))
        method = input("Delivery method (regular/urgent): ").lower()
        card_number = int(input("Card number: "))
        card_name = input("Name on card: ")
        card_expiry = input("Expiration date (YYYY-MM-DD): ")

        cursor.callproc(
            "sp_createorder",
            (client_id, method, "open", card_number, card_name, card_expiry),
        )
        print("✅ Order created successfully.")
    except Exception as e:
        print("Failed to create order:", e)


def add_product_to_order(cursor):
    try:
        order_id = int(input("Order ID: "))
        product_id = int(input("Product ID: "))
        quantity = int(input("Quantity: "))

        cursor.callproc("sp_addproducttoorder", (order_id, product_id, quantity))
        print("✅ Product successfully added to the order.")
    except Exception as e:
        print("Failed to add product to order:", e)


def list_orders_by_day(cursor):
    try:
        date = input("Date (YYYY-MM-DD): ")
        cursor.callproc("sp_dailyorders", (date,))
        for result in cursor.stored_results():
            print("\nOrders:")
            for row in result.fetchall():
                print(
                    f"ID: {row[0]}, Client: {row[1]}, Status: {row[2]}, Delivery: {row[3]}"
                )
    except Exception as e:
        print("Failed to list orders by date:", e)


def get_order_total(cursor):
    try:
        order_id = int(input("Order ID: "))
        cursor.callproc("sp_getordertotal", (order_id,))
        for result in cursor.stored_results():
            row = result.fetchone()
            print(f"Subtotal: €{row[0]:.2f}")
            print(f"VAT: €{row[1]:.2f}")
            print(f"Total: €{row[2]:.2f}")
    except Exception as e:
        print("Failed to calculate order total:", e)


def backup_db():
    fname = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    with open(fname, "w") as out:
        subprocess.run(
            ["mysqldump", "-u", DB_USER, f"-p{DB_PASS}", DB_NAME],
            stdout=out,
            check=True,
        )
    print(f"Backup saved to {fname}")


def list_orders_by_year(cursor):
    try:
        client_id = int(input("Client ID: "))
        year = int(input("Year: "))
        cursor.callproc("sp_annualorders", (client_id, year))
        for result in cursor.stored_results():
            orders = result.fetchall()
            print(f"\nOrders for {year}:")
            for row in orders:
                print(
                    f"ID: {row[0]}, Date: {row[1]}, Status: {row[2]}, Delivery: {row[3]}"
                )
    except Exception as e:
        print("Failed to list orders by year:", e)


def main_menu():
    while True:
        print("\n== BuyPy Back‑Office ==")
        print("1 Clients\n2 Products\n3 Backup DB\n0 Exit")
        ch = input("> ").strip()
        if ch == "1":
            user_menu()
        elif ch == "2":
            product_menu()
        elif ch == "3":
            backup_db()
        elif ch == "0":
            sys.exit()


if __name__ == "__main__":
    if login():
        main_menu()
