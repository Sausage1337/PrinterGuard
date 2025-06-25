"""
Database module for Botsprinter application.
Handles all database operations and schema management.
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from contextlib import contextmanager
import logging

DB_FILE = "office.db"

logging.basicConfig(level=logging.ERROR)

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logging.error(f"Database error: {e}")
        raise DatabaseError(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'operator', 'viewer'))
            )
        ''')
        
        # Check if default admin user exists
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin"), "admin")
            )
        
        # Cabinets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cabinets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Printers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS printers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cabinet_id INTEGER,
                name TEXT NOT NULL,
                cartridge TEXT,
                drum TEXT,
                cartridge_amount INTEGER DEFAULT 0,
                drum_amount INTEGER DEFAULT 0,
                min_cartridge_amount INTEGER DEFAULT 0,
                min_drum_amount INTEGER DEFAULT 0,
                FOREIGN KEY (cabinet_id) REFERENCES cabinets(id)
            )
        ''')
        
        # Writeoff history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS writeoff_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                printer_id INTEGER,
                writeoff_cartridge INTEGER DEFAULT 0,
                writeoff_drum INTEGER DEFAULT 0,
                datetime TEXT NOT NULL,
                username TEXT,
                FOREIGN KEY (printer_id) REFERENCES printers(id)
            )
        ''')
        
        # Storage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                type TEXT CHECK(type IN ('cartridge', 'drum')) NOT NULL,
                amount INTEGER DEFAULT 0
            )
        ''')
        
        # Storage transfer history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS storage_transfer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datetime TEXT NOT NULL,
                username TEXT,
                model TEXT NOT NULL,
                type TEXT CHECK(type IN ('cartridge', 'drum')) NOT NULL,
                amount INTEGER NOT NULL,
                from_place TEXT,
                to_place TEXT
            )
        ''')
        
        conn.commit()


class UserManager:
    """Manages user-related database operations."""
    
    @staticmethod
    def authenticate(login: str, password: str) -> Optional[Tuple[str, str]]:
        """Authenticate a user and return (role, username) if successful."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, login FROM users WHERE login = ? AND password = ?",
                    (login, hash_password(password))
                )
                result = cursor.fetchone()
                return (result[0], result[1]) if result else None
        except DatabaseError:
            return None
    
    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        """Get all users from the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, login, role FROM users ORDER BY login")
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def add_user(login: str, password: str, role: str) -> bool:
        """Add a new user to the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                    (login, hash_password(password), role)
                )
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def update_user(user_id: int, login: str, password: str, role: str) -> bool:
        """Update an existing user."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if password:
                    cursor.execute(
                        "UPDATE users SET login = ?, password = ?, role = ? WHERE id = ?",
                        (login, hash_password(password), role, user_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET login = ?, role = ? WHERE id = ?",
                        (login, role, user_id)
                    )
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Delete a user from the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                return True
        except DatabaseError:
            return False


class CabinetManager:
    """Manages cabinet-related database operations."""
    
    @staticmethod
    def get_all_cabinets() -> List[Dict[str, Any]]:
        """Get all cabinets from the database."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM cabinets ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def add_cabinet(name: str) -> bool:
        """Add a new cabinet to the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cabinets (name) VALUES (?)", (name,))
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def update_cabinet(cabinet_id: int, name: str) -> bool:
        """Update an existing cabinet."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE cabinets SET name = ? WHERE id = ?", (name, cabinet_id))
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def delete_cabinet(cabinet_id: int) -> bool:
        """Delete a cabinet from the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cabinets WHERE id = ?", (cabinet_id,))
                conn.commit()
                return True
        except DatabaseError:
            return False


class PrinterManager:
    """Manages printer-related database operations."""
    
    @staticmethod
    def get_all_printers() -> List[Dict[str, Any]]:
        """Get all printers with cabinet information."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.name, p.cartridge, p.drum, 
                       p.cartridge_amount, p.drum_amount,
                       p.min_cartridge_amount, p.min_drum_amount,
                       c.name as cabinet_name
                FROM printers p
                LEFT JOIN cabinets c ON p.cabinet_id = c.id
                ORDER BY c.name, p.name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def add_printer(cabinet_id: int, name: str, cartridge: str = "", drum: str = "") -> bool:
        """Add a new printer to the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO printers (cabinet_id, name, cartridge, drum) VALUES (?, ?, ?, ?)",
                    (cabinet_id, name, cartridge, drum)
                )
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def update_printer(printer_id: int, **kwargs) -> bool:
        """Update an existing printer."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Build dynamic update query based on provided kwargs
                set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
                values = list(kwargs.values()) + [printer_id]
                
                cursor.execute(
                    f"UPDATE printers SET {set_clause} WHERE id = ?", 
                    values
                )
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def delete_printer(printer_id: int) -> bool:
        """Delete a printer from the database."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM printers WHERE id = ?", (printer_id,))
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def get_low_stock_warnings() -> List[str]:
        """Get warnings for printers with low stock."""
        warnings = []
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, cartridge, cartridge_amount, min_cartridge_amount,
                       drum, drum_amount, min_drum_amount
                FROM printers
            ''')
            
            for row in cursor.fetchall():
                name = row['name']
                cart_amt = row['cartridge_amount']
                min_cart = row['min_cartridge_amount']
                drum_amt = row['drum_amount']
                min_drum = row['min_drum_amount']
                
                if min_cart and cart_amt is not None and cart_amt < min_cart:
                    warnings.append(
                        f"Внимание: В принтере <b>{name}</b> мало картриджей "
                        f"({cart_amt} / минимум {min_cart})"
                    )
                
                if min_drum and drum_amt is not None and drum_amt < min_drum:
                    warnings.append(
                        f"Внимание: В принтере <b>{name}</b> мало драмов "
                        f"({drum_amt} / минимум {min_drum})"
                    )
                
                if cart_amt is not None and cart_amt < 0:
                    warnings.append(
                        f"ОШИБКА: В принтере <b>{name}</b> отрицательный запас "
                        f"картриджей ({cart_amt})"
                    )
                
                if drum_amt is not None and drum_amt < 0:
                    warnings.append(
                        f"ОШИБКА: В принтере <b>{name}</b> отрицательный запас "
                        f"драмов ({drum_amt})"
                    )
        
        return warnings


class StorageManager:
    """Manages storage-related database operations."""
    
    @staticmethod
    def get_all_storage() -> List[Dict[str, Any]]:
        """Get all storage items."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT model, type, amount FROM storage ORDER BY type, model")
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def add_to_storage(model: str, item_type: str, amount: int, username: str) -> bool:
        """Add items to storage."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if item already exists
                cursor.execute(
                    "SELECT id, amount FROM storage WHERE model = ? AND type = ?",
                    (model, item_type)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing item
                    new_amount = existing['amount'] + amount
                    cursor.execute(
                        "UPDATE storage SET amount = ? WHERE id = ?",
                        (new_amount, existing['id'])
                    )
                else:
                    # Insert new item
                    cursor.execute(
                        "INSERT INTO storage (model, type, amount) VALUES (?, ?, ?)",
                        (model, item_type, amount)
                    )
                
                # Add to transfer history
                cursor.execute('''
                    INSERT INTO storage_transfer_history 
                    (datetime, username, model, type, amount, from_place, to_place)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    username, model, item_type, amount,
                    "внешние поставки", "склад"
                ))
                
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def transfer_to_printer(model: str, item_type: str, amount: int, 
                          printer_id: int, username: str) -> bool:
        """Transfer items from storage to printer."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Проверка остатка на складе
                cursor.execute(
                    "SELECT amount FROM storage WHERE model = ? AND type = ?",
                    (model, item_type)
                )
                row = cursor.fetchone()
                if not row or row['amount'] < amount:
                    return False
                # Update storage
                cursor.execute(
                    "UPDATE storage SET amount = amount - ? WHERE model = ? AND type = ?",
                    (amount, model, item_type)
                )
                # Update printer
                if item_type == "cartridge":
                    cursor.execute(
                        "UPDATE printers SET cartridge_amount = cartridge_amount + ? WHERE id = ?",
                        (amount, printer_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE printers SET drum_amount = drum_amount + ? WHERE id = ?",
                        (amount, printer_id)
                    )
                # Get printer name for history
                cursor.execute("SELECT name FROM printers WHERE id = ?", (printer_id,))
                printer_name = cursor.fetchone()['name']
                # Add to transfer history
                cursor.execute('''
                    INSERT INTO storage_transfer_history 
                    (datetime, username, model, type, amount, from_place, to_place)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    username, model, item_type, amount,
                    "склад", printer_name
                ))
                conn.commit()
                return True
        except DatabaseError:
            return False
    
    @staticmethod
    def get_compatible_printers(model: str, item_type: str) -> List[Dict[str, Any]]:
        """Get printers compatible with the given supply model."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if item_type == "cartridge":
                cursor.execute("SELECT id, name FROM printers WHERE cartridge = ?", (model,))
            else:
                cursor.execute("SELECT id, name FROM printers WHERE drum = ?", (model,))
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_storage_summary() -> Dict[str, int]:
        """Get summary of storage quantities."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(amount) FROM storage WHERE type = 'cartridge'")
            cartridge_sum = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(amount) FROM storage WHERE type = 'drum'")
            drum_sum = cursor.fetchone()[0] or 0
            
            return {"cartridges": cartridge_sum, "drums": drum_sum}
    
    @staticmethod
    def set_storage_amount(model: str, item_type: str, amount: int) -> bool:
        """Установить новое количество для расходника на складе."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE storage SET amount = ? WHERE model = ? AND type = ?",
                    (amount, model, item_type)
                )
                conn.commit()
                return cursor.rowcount > 0
        except DatabaseError:
            return False
    
    @staticmethod
    def add_writeoff_record(printer_id: int, writeoff_cartridge: int, writeoff_drum: int, username: str) -> bool:
        """Добавить запись о замене/списании расходников в writeoff_history."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO writeoff_history (printer_id, writeoff_cartridge, writeoff_drum, datetime, username)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (printer_id, writeoff_cartridge, writeoff_drum, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username)
                )
                # Одновременно уменьшаем количество расходников у принтера
                if writeoff_cartridge > 0:
                    cursor.execute(
                        "UPDATE printers SET cartridge_amount = cartridge_amount - ? WHERE id = ?",
                        (writeoff_cartridge, printer_id)
                    )
                if writeoff_drum > 0:
                    cursor.execute(
                        "UPDATE printers SET drum_amount = drum_amount - ? WHERE id = ?",
                        (writeoff_drum, printer_id)
                    )
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Ошибка записи списания: {e}")
            return False


class HistoryManager:
    """Manages history-related database operations."""
    
    @staticmethod
    def get_transfer_history() -> List[Dict[str, Any]]:
        """Get all transfer history records."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT datetime, username, model, type, amount, from_place, to_place
                FROM storage_transfer_history
                ORDER BY datetime DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_writeoff_history() -> List[Dict[str, Any]]:
        """Get all writeoff history records."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT wh.datetime, wh.username, wh.writeoff_cartridge, 
                       wh.writeoff_drum, p.name as printer_name
                FROM writeoff_history wh
                JOIN printers p ON wh.printer_id = p.id
                ORDER BY wh.datetime DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
