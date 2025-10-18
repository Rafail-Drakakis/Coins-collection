from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from pathlib import Path
from tabulate import tabulate
from contextlib import contextmanager

app = Flask(__name__)
DB_PATH = Path("coins.db")

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS coins(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            denomination TEXT NOT NULL,
            year INTEGER NOT NULL,
            exists_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(country, denomination, year)
        )
        """)

        # Ensure legacy databases are migrated to the new schema
        cur.execute("PRAGMA table_info(coins)")
        columns = {row[1] for row in cur.fetchall()}

        if "exists_count" not in columns and "exists_flag" in columns:
            try:
                cur.execute("ALTER TABLE coins RENAME COLUMN exists_flag TO exists_count")
                columns.add("exists_count")
            except sqlite3.OperationalError:
                cur.execute("ALTER TABLE coins ADD COLUMN exists_count INTEGER NOT NULL DEFAULT 0")
                cur.execute("UPDATE coins SET exists_count = exists_flag")
                columns.add("exists_count")

        if "exists_count" not in columns:
            cur.execute("ALTER TABLE coins ADD COLUMN exists_count INTEGER NOT NULL DEFAULT 0")

        cur.execute(
            "UPDATE coins SET exists_count = CASE WHEN exists_count < 1 THEN 1 ELSE exists_count END"
        )


init_db()

@app.route("/")
def index():
    """Render the main page"""
    return render_template("index.html")

@app.route("/coins", methods=["GET"])
def get_coins():
    """Get all coins from the database"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM coins ORDER BY year DESC, country ASC")
            data = [dict(row) for row in cur.fetchall()]
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/coins", methods=["POST"])
def add_coin():
    """Add a new coin or update existing one"""
    try:
        data = request.json
        
        # Validate input
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        required_fields = ["country", "denomination", "year"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        country = data["country"].strip()
        denomination = data["denomination"].strip()
        
        # Validate data
        if not country or not denomination:
            return jsonify({"error": "Country and denomination cannot be empty"}), 400
        
        try:
            year = int(data["year"])
            if year < 1 or year > 9999:
                return jsonify({"error": "Year must be between 1 and 9999"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Year must be a valid integer"}), 400
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if coin already exists
            cur.execute(
                """
                SELECT id, exists_count FROM coins
                WHERE country=? AND denomination=? AND year=?
                """,
                (country, denomination, year),
            )
            existing = cur.fetchone()

            if not existing:
                # Insert new coin
                cur.execute(
                    """
                    INSERT INTO coins (country, denomination, year, exists_count)
                    VALUES (?, ?, ?, 1)
                    """,
                    (country, denomination, year),
                )
                status = "added"
            else:
                # Update existing coin count
                cur.execute(
                    """
                    UPDATE coins
                    SET exists_count = exists_count + 1
                    WHERE country=? AND denomination=? AND year=?
                    """,
                    (country, denomination, year),
                )
                status = "incremented"

        return jsonify({"status": status}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/coins/<int:coin_id>", methods=["DELETE"])
def delete_coin(coin_id):
    """Delete a coin by ID or decrement its count"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, exists_count FROM coins WHERE id=?", (coin_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Coin not found"}), 404

            _, count = row
            if count > 1:
                cur.execute(
                    "UPDATE coins SET exists_count = exists_count - 1 WHERE id=?",
                    (coin_id,),
                )
                status = "decremented"
            else:
                cur.execute("DELETE FROM coins WHERE id=?", (coin_id,))
                status = "deleted"

        return jsonify({"status": status}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def show_db():
    """Interactive database viewer for CLI"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                print("No tables found in the database.")
                return
            
            print("\nAvailable tables:")
            for table in tables:
                print(f"  - {table[0]}")
            
            table_name = input("\nWhich table do you want to see? ").strip()
            
            if not table_name:
                print("No table name provided.")
                return
            
            # Validate table name exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            if not cursor.fetchone():
                print(f"Table '{table_name}' does not exist.")
                return
            
            # Safe to query now since we validated the table exists
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            print(f"\nContents of '{table_name}':")
            if rows:
                print(tabulate(rows, headers=columns, tablefmt="grid"))
            else:
                print("(Table is empty)")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Coin Collection Manager")
    init_db()
    app.run(debug=True)
