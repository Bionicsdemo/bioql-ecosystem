# Copyright 2024-2025 SpectrixRD
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license text

"""
Mock Database for testing
"""

import os
import sqlite3
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional


class MockDatabase:
    """Mock SQLite database for testing"""

    def __init__(self, in_memory: bool = True):
        """Initialize mock database"""
        if in_memory:
            self.db_path = ":memory:"
        else:
            # Create temporary file
            fd, self.db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)

        self.connection = None
        self.setup_schema()

    def setup_schema(self):
        """Create database schema"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        cursor = self.connection.cursor()

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                tier TEXT DEFAULT 'free',
                balance REAL DEFAULT 0.0,
                stripe_customer_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Usage table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                shots INTEGER NOT NULL,
                backend TEXT NOT NULL,
                cost REAL NOT NULL,
                qec_enabled BOOLEAN DEFAULT 0,
                qec_distance INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        # LLM usage table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                query TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """
        )

        self.connection.commit()

    def create_user(self, user_id: str, email: str, api_key: str, tier: str = "free") -> bool:
        """Create user"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "INSERT INTO users (user_id, email, api_key, tier) VALUES (?, ?, ?, ?)",
                (user_id, email, api_key, tier),
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get user by API key"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    def update_user_balance(self, user_id: str, amount: float) -> bool:
        """Update user balance"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE users SET balance = balance + ?, updated_at = ? WHERE user_id = ?",
                (amount, datetime.now(), user_id),
            )
            self.connection.commit()
            return True
        except Exception:
            return False

    def record_usage(
        self,
        user_id: str,
        shots: int,
        backend: str,
        cost: float,
        qec_enabled: bool = False,
        qec_distance: int = None,
    ) -> bool:
        """Record quantum usage"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """INSERT INTO usage (user_id, shots, backend, cost, qec_enabled, qec_distance)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, shots, backend, cost, qec_enabled, qec_distance),
            )
            self.connection.commit()
            return True
        except Exception:
            return False

    def record_llm_usage(
        self, user_id: str, query: str, model: str, tokens: int, cost: float
    ) -> bool:
        """Record LLM usage"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """INSERT INTO llm_usage (user_id, query, model, tokens, cost)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, query, model, tokens, cost),
            )
            self.connection.commit()
            return True
        except Exception:
            return False

    def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics"""
        cursor = self.connection.cursor()

        # Quantum usage
        cursor.execute(
            "SELECT COUNT(*), SUM(shots), SUM(cost) FROM usage WHERE user_id = ?", (user_id,)
        )
        quantum_stats = cursor.fetchone()

        # LLM usage
        cursor.execute(
            "SELECT COUNT(*), SUM(tokens), SUM(cost) FROM llm_usage WHERE user_id = ?", (user_id,)
        )
        llm_stats = cursor.fetchone()

        return {
            "quantum": {
                "executions": quantum_stats[0] or 0,
                "total_shots": quantum_stats[1] or 0,
                "total_cost": quantum_stats[2] or 0.0,
            },
            "llm": {
                "queries": llm_stats[0] or 0,
                "total_tokens": llm_stats[1] or 0,
                "total_cost": llm_stats[2] or 0.0,
            },
        }

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def reset(self):
        """Reset database (clear all data)"""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM llm_usage")
        cursor.execute("DELETE FROM usage")
        cursor.execute("DELETE FROM users")
        self.connection.commit()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        if self.db_path != ":memory:" and os.path.exists(self.db_path):
            os.unlink(self.db_path)
