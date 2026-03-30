"""SQL security utilities - High-risk keyword detection and password encryption"""

import os
import re
import base64
from typing import List, Tuple, Optional

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from environment."""
    key = os.getenv("PASSWORD_ENCRYPTION_KEY")
    if key:
        return key.encode() if isinstance(key, str) else key
    # Default: generate a new key (will change on every restart - not for production!)
    return Fernet.generate_key()


# Module-level Fernet instance for consistent encryption/decryption
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create Fernet instance with the encryption key."""
    global _fernet
    if _fernet is None:
        key = _get_encryption_key()
        _fernet = Fernet(key)
    return _fernet


def encrypt_password(plain_password: str) -> str:
    """Encrypt a password for storage."""
    if not plain_password:
        return ""

    if not HAS_CRYPTO:
        import base64
        return base64.b64encode(plain_password.encode()).decode()

    f = _get_fernet()
    encrypted = f.encrypt(plain_password.encode())
    return encrypted.decode()  # Fernet.encrypt returns bytes, decode to str


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a stored password."""
    if not encrypted_password:
        return ""

    if not HAS_CRYPTO:
        import base64
        return base64.b64decode(encrypted_password.encode()).decode()

    try:
        f = _get_fernet()
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception:
        # If decryption fails, try the fallback (for existing unencrypted passwords)
        import base64
        try:
            return base64.b64decode(encrypted_password.encode()).decode()
        except Exception:
            return encrypted_password


# High-risk SQL keywords (DDL/DML)
HIGH_RISK_KEYWORDS: List[str] = [
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
    "GRANT",
    "REVOKE",
    "INSERT",
    "UPDATE",
    "CREATE",
    "EXECUTE",
    "EXEC",
    "LOAD",
    "LOAD_FILE",
    "INTO OUTFILE",
    "BENCHMARK",
    "SLEEP",
    "SHUTDOWN",
]

# Patterns for dangerous SQL constructs
DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
    (r"\bxp_cmdshell\b", "xp_cmdshell 存储过程"),
    (r"\bxp_execresultset\b", "xp_execresultset 存储过程"),
    (r"\bsp_executesql\b", "sp_executesql 存储过程"),
    (r"\bexec\s*\(", "EXEC/EXECUTE 语句"),
    (r"\bshutdown\s+--", "SHUTDOWN 命令"),
]


def check_sql_keywords(sql: str) -> Tuple[bool, str]:
    """
    Check if SQL contains high-risk keywords.

    Args:
        sql: SQL statement to check

    Returns:
        Tuple of (is_safe, reason_if_unsafe)
    """
    sql_upper = sql.upper()

    # Check high-risk keywords
    for keyword in HIGH_RISK_KEYWORDS:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"禁止关键字: {keyword}"

    # Check dangerous patterns
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return False, f"危险模式: {description}"

    return True, ""


def sanitize_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifier (table name, column name).

    Args:
        identifier: Raw identifier from user input

    Returns:
        Sanitized identifier safe for SQL queries
    """
    # Only allow alphanumeric and underscore
    return re.sub(r'[^a-zA-Z0-9_]', '', identifier)
