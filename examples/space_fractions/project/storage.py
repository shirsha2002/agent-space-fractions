"""Storage layer for Space Fractions.
Uses SQLite in a per-user application data directory.
"""
import os
import sqlite3
import hashlib
import secrets
import json
from pathlib import Path
from typing import List, Optional, Tuple
from fractions import Fraction

# Default questions (original sixth-grade fraction questions)
DEFAULT_QUESTIONS = [
    {
        'qid': 'Q1',
        'prompt': 'What is 1/2 + 1/4?',
        'options': ['1/2', '3/4', '1/4', '2/6'],
        'answer': '3/4',
        'explanation': 'Find a common denominator: 1/2 = 2/4, so 2/4 + 1/4 = 3/4.'
    },
    {
        'qid': 'Q2',
        'prompt': 'Simplify 4/8.',
        'options': ['1/2', '3/4', '2/3', '5/8'],
        'answer': '1/2',
        'explanation': 'Divide numerator and denominator by 4.'
    },
    {
        'qid': 'Q3',
        'prompt': 'Which fraction is equivalent to 2/3?',
        'options': ['3/4', '4/6', '5/8', '2/5'],
        'answer': '4/6',
        'explanation': 'Multiply numerator and denominator by 2.'
    },
    {
        'qid': 'Q4',
        'prompt': 'What is 3/5 - 1/5?',
        'options': ['1/5', '2/5', '3/5', '4/5'],
        'answer': '2/5',
        'explanation': 'Subtract the numerators: 3 - 1 = 2.'
    },
    {
        'qid': 'Q5',
        'prompt': 'What is 2/3 of 12?',
        'options': ['6', '8', '9', '10'],
        'answer': '8',
        'explanation': 'Multiply: (2/3) * 12 = 8.'
    },
    {
        'qid': 'Q6',
        'prompt': 'Compare: 5/8 and 3/4. Which is larger?',
        'options': ['5/8', '3/4', 'They are equal', 'Cannot tell'],
        'answer': '3/4',
        'explanation': 'Convert to common denominator: 5/8 = 0.625, 3/4 = 0.75.'
    },
    {
        'qid': 'Q7',
        'prompt': 'What is 1/3 + 1/6?',
        'options': ['1/2', '1/3', '1/6', '2/3'],
        'answer': '1/2',
        'explanation': '1/3 = 2/6, so 2/6 + 1/6 = 3/6 = 1/2.'
    },
    {
        'qid': 'Q8',
        'prompt': 'Simplify 6/9.',
        'options': ['2/3', '3/4', '4/5', '1/2'],
        'answer': '2/3',
        'explanation': 'Divide numerator and denominator by 3.'
    },
    {
        'qid': 'Q9',
        'prompt': 'What is 5/6 - 1/3?',
        'options': ['1/2', '1/3', '1/6', '2/3'],
        'answer': '1/2',
        'explanation': '1/3 = 2/6, so 5/6 - 2/6 = 3/6 = 1/2.'
    },
    {
        'qid': 'Q10',
        'prompt': 'What is 3/4 of 20?',
        'options': ['12', '15', '18', '10'],
        'answer': '15',
        'explanation': 'Multiply: (3/4) * 20 = 15.'
    },
]

class Storage:
    """Handles SQLite persistence for questions, scores, and users."""
    MIN_PASSWORD_LENGTH = 8

    def __init__(self, db_path: Optional[str] = None):
        """Initialize storage. If db_path is None, use per-user app data directory."""
        if db_path is None:
            app_dir = self._get_app_data_dir()
            db_path = str(app_dir / 'space_fractions.db')
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._active_user = None
        self._create_tables()
        self._seed_default_questions()
        self._seed_admin_unconfigured()

    def _get_app_data_dir(self) -> Path:
        """Return per-user writable application data directory, creating it if necessary."""
        # On Windows, use %APPDATA%\SpaceFractions; on Linux/Mac, ~/.local/share/SpaceFractions
        base = os.environ.get('APPDATA', str(Path.home() / '.local' / 'share'))
        app_dir = Path(base) / 'SpaceFractions'
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                qid TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                options TEXT NOT NULL,  -- JSON list
                answer TEXT NOT NULL,
                explanation TEXT NOT NULL DEFAULT ''
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
        ''')
        self.conn.commit()

    def _seed_default_questions(self):
        """Insert default questions if none exist."""
        cur = self.conn.cursor()
        cur.execute('SELECT COUNT(*) FROM questions')
        count = cur.fetchone()[0]
        if count == 0:
            for q in DEFAULT_QUESTIONS:
                cur.execute('''
                    INSERT OR IGNORE INTO questions (qid, prompt, options, answer, explanation)
                    VALUES (?, ?, ?, ?, ?)
                ''', (q['qid'], q['prompt'], json.dumps(q['options']), q['answer'], q['explanation']))
            self.conn.commit()

    def _seed_admin_unconfigured(self):
        """Ensure admin user exists but cannot authenticate until password set."""
        cur = self.conn.cursor()
        cur.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
        if cur.fetchone()[0] == 0:
            # Create admin with a random salt and a hash of an impossible password.
            # The user must set a password through the admin panel.
            salt = secrets.token_hex(16)
            hash_value = hashlib.pbkdf2_hmac('sha256', b'', bytes.fromhex(salt), 100000).hex()
            cur.execute('INSERT OR IGNORE INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)',
                        ('admin', hash_value, salt, 'admin'))
            self.conn.commit()

    def is_admin_password_set(self, username: str = 'admin') -> bool:
        """Return True if admin password is set (i.e., hash is not empty password)."""
        cur = self.conn.cursor()
        cur.execute('SELECT salt, password_hash FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        if not row:
            return False
        empty_hash = hashlib.pbkdf2_hmac('sha256', b'', bytes.fromhex(row['salt']), 100000).hex()
        return row['password_hash'] != empty_hash

    def get_questions(self) -> List['Question']:
        """Return list of Question objects."""
        from game_core import Question
        cur = self.conn.cursor()
        cur.execute('SELECT qid, prompt, options, answer, explanation FROM questions ORDER BY qid')
        questions = []
        for row in cur.fetchall():
            options = json.loads(row['options'])
            questions.append(Question(row['qid'], row['prompt'], options, row['answer'], row['explanation']))
        return questions

    def logout(self):
        """Invalidate the local authenticated session."""
        self._active_user = None

    def _require_admin(self):
        if not self._active_user or self.get_user_roles(self._active_user) != 'admin':
            raise PermissionError("An authenticated administrator is required")

    def update_question(self, qid, prompt, options, answer, explanation=''):
        """Validate before writing, and authorize using the authenticated session."""
        self._require_admin()
        if not isinstance(qid, str) or not qid.strip() or len(qid) > 64:
            raise ValueError("A non-empty question identifier is required")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1000:
            raise ValueError("A non-empty prompt of at most 1000 characters is required")
        if not isinstance(options, (list, tuple)) or not 2 <= len(options) <= 10:
            raise ValueError("Provide between two and ten choices")
        if not all(isinstance(opt, str) and opt.strip() and len(opt) <= 120 for opt in options):
            raise ValueError("Choices must be non-empty text of at most 120 characters")
        options = [opt.strip() for opt in options]
        if len({opt.casefold() for opt in options}) != len(options):
            raise ValueError("Choices must be distinct")
        if not isinstance(answer, str) or answer.strip() not in options:
            raise ValueError("The answer must be one of the choices")
        answer = answer.strip()
        try:
            correct = Fraction(answer)
        except (ValueError, ZeroDivisionError):
            raise ValueError("The correct answer must be a valid fraction or integer") from None
        matches = 0
        for option in options:
            try:
                matches += Fraction(option) == correct
            except (ValueError, ZeroDivisionError):
                # Text distractors such as 'They are equal' are legitimate.
                # Numeric-looking malformed fractions are not.
                if '/' in option or any(character.isdigit() for character in option):
                    raise ValueError("A numeric choice is not a valid fraction") from None
        if matches != 1:
            raise ValueError("Exactly one choice must be mathematically correct")
        if not isinstance(explanation, str) or len(explanation) > 2000:
            raise ValueError("Explanation must be text of at most 2000 characters")
        with self.conn:
            self.conn.execute(
                'INSERT OR REPLACE INTO questions (qid,prompt,options,answer,explanation) VALUES (?,?,?,?,?)',
                (qid.strip(), prompt.strip(), json.dumps(options), answer, explanation.strip()))

    def add_score(self, username: str, score: int, total_questions: int) -> None:
        """Record a game score."""
        cur = self.conn.cursor()
        cur.execute('INSERT INTO scores (username, score, total_questions) VALUES (?, ?, ?)',
                    (username, score, total_questions))
        self.conn.commit()

    def get_score_history(self, username: Optional[str] = None) -> List[sqlite3.Row]:
        """Return score rows, optionally filtered by username."""
        cur = self.conn.cursor()
        if username:
            cur.execute('SELECT * FROM scores WHERE username = ? ORDER BY date DESC, id DESC', (username,))
        else:
            cur.execute('SELECT * FROM scores ORDER BY date DESC, id DESC')
        return cur.fetchall()

    def set_user_password(self, username: str, password: str) -> None:
        """Create a player, bootstrap admin once, or change an authorized password."""
        if not isinstance(username, str) or not username.strip() or len(username) > 64:
            raise ValueError("A username of at most 64 characters is required")
        username = username.strip()
        if not isinstance(password, str) or not self.MIN_PASSWORD_LENGTH <= len(password) <= 1024:
            raise ValueError("Password must contain between 8 and 1024 characters")
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            existing = self.conn.execute('SELECT role FROM users WHERE username=?', (username,)).fetchone()
            if existing:
                bootstrap = username == 'admin' and existing['role'] == 'admin' and not self.is_admin_password_set(username)
                authorized = self._active_user == username or (self._active_user and self.get_user_roles(self._active_user) == 'admin')
                if not bootstrap and not authorized:
                    raise PermissionError("Login is required before changing an existing password")
            elif username.casefold() == 'admin':
                raise ValueError("That username is reserved")
            salt = secrets.token_hex(16)
            digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf8'), bytes.fromhex(salt), 100000).hex()
            if existing:
                self.conn.execute('UPDATE users SET password_hash=?,salt=? WHERE username=?', (digest, salt, username))
            else:
                self.conn.execute('INSERT INTO users(username,password_hash,salt,role) VALUES(?,?,?,?)', (username,digest,salt,'user'))

    def verify_user(self, username: str, password: str) -> Tuple[bool, str]:
        """Verify credentials. Returns (success, role). Admin with unset password cannot authenticate."""
        self.logout()
        cur = self.conn.cursor()
        cur.execute('SELECT password_hash, salt, role FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        if not row:
            return False, ''
        salt = row['salt']
        stored_hash = row['password_hash']
        # If admin and password not set, reject
        if row['role'] == 'admin' and not self.is_admin_password_set(username):
            return False, ''
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000).hex()
        if secrets.compare_digest(computed_hash, stored_hash):
            self._active_user = username
            return True, row['role']
        return False, ''

    def get_user_roles(self, username: str) -> Optional[str]:
        """Return role for username or None."""
        cur = self.conn.cursor()
        cur.execute('SELECT role FROM users WHERE username = ?', (username,))
        row = cur.fetchone()
        return row['role'] if row else None

    def close(self):
        self.conn.close()
