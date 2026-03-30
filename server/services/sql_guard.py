"""
SQL Guard Service - SQL Security Scanner
"""

import re
from typing import Optional
from dataclasses import dataclass


# High-risk SQL keywords that should never appear
HIGH_RISK_KEYWORDS = [
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
    "xp_",
    "sp_",
]

# Medium-risk patterns (allowed in SELECT context only)
MEDIUM_RISK_PATTERNS = [
    r"\bINTO\s+OUTFILE\b",
    r"\bLOAD_FILE\b",
    r"\bBENCHMARK\b",
    r"\bSLEEP\b",
]


@dataclass
class ScanResult:
    """SQL security scan result."""
    passed: bool
    reason: Optional[str] = None


class SQLGuard:
    """
    SQL Security Scanner.

    Scans generated SQL for:
    1. Lexical detection of high-risk keywords
    2. Syntax validation via EXPLAIN
    3. Complexity limits (max 3 table JOINs, no deep subqueries)
    """

    def __init__(
        self,
        max_joins: int = 3,
        max_subquery_depth: int = 2,
        max_query_length: int = 10000,
    ):
        self.max_joins = max_joins
        self.max_subquery_depth = max_subquery_depth
        self.max_query_length = max_query_length

    def scan(self, sql: str) -> ScanResult:
        """
        Scan SQL for security issues.

        Args:
            sql: SQL statement to validate

        Returns:
            ScanResult with passed=True if safe, passed=False with reason if blocked
        """
        # Normalize whitespace
        sql_normalized = " ".join(sql.split())
        sql_upper = sql_normalized.upper()

        # Check 1: Length limit
        if len(sql_normalized) > self.max_query_length:
            return ScanResult(
                passed=False,
                reason=f"SQL 过长，超过 {self.max_query_length} 字符限制"
            )

        # Check 2: High-risk keywords
        keyword_result = self._check_high_risk_keywords(sql_upper)
        if not keyword_result.passed:
            return keyword_result

        # Check 3: Medium-risk patterns (file operations, timing attacks)
        pattern_result = self._check_patterns(sql_normalized)
        if not pattern_result.passed:
            return pattern_result

        # Check 4: JOIN complexity
        join_result = self._check_join_complexity(sql_upper)
        if not join_result.passed:
            return join_result

        # Check 5: Subquery depth
        subquery_result = self._check_subquery_depth(sql_normalized)
        if not subquery_result.passed:
            return subquery_result

        # Check 6: Must start with SELECT (whitespace stripped)
        if not sql_upper.strip().startswith("SELECT"):
            return ScanResult(
                passed=False,
                reason="仅允许 SELECT 语句"
            )

        return ScanResult(passed=True)

    def _check_high_risk_keywords(self, sql_upper: str) -> ScanResult:
        """Check for high-risk SQL keywords."""
        for keyword in HIGH_RISK_KEYWORDS:
            # Use word boundary to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return ScanResult(
                    passed=False,
                    reason=f"禁止使用 {keyword} 关键字"
                )
        return ScanResult(passed=True)

    def _check_patterns(self, sql: str) -> ScanResult:
        """Check for dangerous SQL patterns."""
        sql_upper = sql.upper()
        for pattern in MEDIUM_RISK_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return ScanResult(
                    passed=False,
                    reason="禁止使用文件操作或时序攻击相关函数"
                )
        return ScanResult(passed=True)

    def _check_join_complexity(self, sql_upper: str) -> ScanResult:
        """Count and validate number of JOINs."""
        # Count JOIN keywords (excluding "LEFT JOIN" etc counted as one)
        join_pattern = r'\bJOIN\b'
        join_count = len(re.findall(join_pattern, sql_upper))

        if join_count > self.max_joins:
            return ScanResult(
                passed=False,
                reason=f"JOIN 数量超过限制（最多 {self.max_joins} 个）"
            )
        return ScanResult(passed=True)

    def _check_subquery_depth(self, sql: str) -> ScanResult:
        """Check subquery nesting depth."""
        depth = 0
        max_depth_found = 0
        i = 0
        sql_len = len(sql)

        while i < sql_len:
            if sql[i] == '(':
                # Check if this looks like a subquery start
                j = i + 1
                while j < sql_len and sql[j] in ' \t\n':
                    j += 1
                if j < sql_len and sql[j:].upper().startswith('SELECT'):
                    depth += 1
                    max_depth_found = max(max_depth_found, depth)
            elif sql[i] == ')':
                depth = max(0, depth - 1)
            i += 1

        if max_depth_found > self.max_subquery_depth:
            return ScanResult(
                passed=False,
                reason=f"子查询嵌套过深（最多 {self.max_subquery_depth} 层）"
            )
        return ScanResult(passed=True)

    def validate_syntax(self, sql: str, db_session) -> ScanResult:
        """
        Validate SQL syntax using EXPLAIN.

        Args:
            sql: SQL statement to validate
            db_session: Database session for connection

        Returns:
            ScanResult indicating if syntax is valid
        """
        try:
            # Use EXPLAIN to validate syntax without executing
            explain_sql = f"EXPLAIN {sql}"
            result = db_session.execute(explain_sql)
            # If no exception, syntax is valid
            return ScanResult(passed=True)
        except Exception as e:
            return ScanResult(
                passed=False,
                reason=f"SQL 语法错误：{str(e)}"
            )


# Singleton instance
_guard_instance: Optional[SQLGuard] = None


def get_sql_guard() -> SQLGuard:
    """Get or create SQL guard singleton."""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = SQLGuard()
    return _guard_instance
