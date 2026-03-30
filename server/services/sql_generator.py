"""
SQL Generator Service - NL → SQL using LangChain + LLM
"""

import json
import logging
from typing import Optional, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from server.db.database import get_db_session
from server.services.ai_model_service import AIModelService


# Base prompt template for SQL generation
BASE_SQL_GEN_PROMPT = """你是一个 SQL 专家。根据以下数据库表结构，将用户的问题翻译成 SQL 语句。

【表结构】
{schema_info}

【业务术语说明】
{terminology_info}

【用户问题】
{user_query}

【重要要求】
1. 只输出 SQL 语句，不要输出任何分析、解释、思考过程或 markdown 格式
2. 只生成 SELECT 语句，禁止 DELETE/DROP/INSERT/UPDATE
3. 必须使用正确的表名和列名
4. 必须指定 LIMIT（最大1000）

【表选择策略】
- 如果问题提到"入库"，检查 inbound_ 开头的表
- 如果问题提到"产品"，检查 product_ 开头的表或包含 product_name 列的表
- 如果问题提到"订单"，检查 order_ 开头的表
- xxx_detail 明细表通常包含主表的汇总字段（如 total_amount）

【外键关联原则】
- xxx_id 结尾的列是外键，关联 xxx 表
- 主表 id 关联明细表的外键
- 多表查询必须用 JOIN

【时间表达式转换规则】
自然语言时间表达必须转换为具体日期值：
- "今天" → CURRENT_DATE（日期类型，不带时间）
- "昨天" → CURRENT_DATE - INTERVAL '1 day'
- "前天" → CURRENT_DATE - INTERVAL '2 days'
- "明天" → CURRENT_DATE + INTERVAL '1 day'
- "本周" → DATE_TRUNC('week', CURRENT_DATE)
- "本月" → DATE_TRUNC('month', CURRENT_DATE)
- "今年" → DATE_TRUNC('year', CURRENT_DATE)
- "上月" → DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
- "下月" → DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
- "最近N天" → CURRENT_DATE - INTERVAL 'N day'（如"最近7天" → CURRENT_DATE - INTERVAL '7 days'）
- "今天之前" → < CURRENT_DATE（不含今天）
- "今天之后" → >= CURRENT_DATE + INTERVAL '1 day'（不含今天）
- "截至今天" → <= CURRENT_DATE
- 时间比较用 >= > < <= 运算符，配合 CURRENT_DATE 和 INTERVAL 表达式
- 禁止将中文日期直接作为字符串（如 '今天'、'今天之前' 都是错误的）

【示例】
Q: 入库金额大于1000的产品
A: SELECT DISTINCT ird.product_name FROM inbound_record ir JOIN inbound_record_detail ird ON ir.id = ird.inbound_record_id WHERE ir.total_amount > 1000 LIMIT 1000

Q: 每个类别的订单数量
A: SELECT category, COUNT(*) as cnt FROM orders GROUP BY category LIMIT 1000

Q: 今天之前入库的产品
A: SELECT * FROM inbound_record WHERE create_time < CURRENT_DATE LIMIT 1000

Q: 最近7天内的订单
A: SELECT * FROM orders WHERE create_time >= CURRENT_DATE - INTERVAL '7 days' LIMIT 1000

请只输出 SQL：
"""


class SQLGenerator:
    """NL to SQL generator using LangChain"""

    def __init__(
        self,
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        api_domain: Optional[str] = None,
        supplier: str = "openai",
    ):
        """Initialize SQL Generator.

        Args:
            llm_model: Model name (e.g., gpt-4o-mini)
            temperature: LLM temperature
            api_key: API key (optional, will use default if not provided)
            api_domain: API domain (optional)
            supplier: LLM supplier (openai, zhipu, qianfan, etc.)
        """
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature,
            api_key=api_key,
            base_url=api_domain,
            max_tokens=4000,  # 增加避免截断
        )
        self.supplier = supplier

    def _build_schema_context(
        self,
        db: Session,
        datasource_id: int,
    ) -> str:
        """Build schema context from database metadata."""
        query = text("""
            SELECT
                t.table_name,
                t.table_comment,
                c.column_name,
                c.data_type,
                c.column_comment
            FROM schema_tables t
            LEFT JOIN schema_columns c ON t.id = c.table_id
            WHERE t.datasource_id = :datasource_id
            ORDER BY t.table_name, c.column_id
        """)
        result = db.execute(query, {"datasource_id": datasource_id})
        rows = result.fetchall()

        tables: dict[str, dict] = {}
        for row in rows:
            table_name = row[0]
            if table_name not in tables:
                tables[table_name] = {
                    "comment": row[1] or "",
                    "columns": []
                }
            if row[2]:
                tables[table_name]["columns"].append({
                    "column_name": row[2],
                    "data_type": row[3],
                    "comment": row[4] or "",
                })

        # Build schema with better semantic hints
        schema_parts = []
        fk_hints = []  # Store foreign key relationships
        table_names_lower = {t: t.lower() for t in tables.keys()}  # For fuzzy matching

        # Common column name patterns with Chinese semantic hints
        semantic_map = {
            'product_name': '产品名称',
            'product': '产品',
            'amount': '金额/数量',
            'total_amount': '总金额',
            'price': '价格',
            'quantity': '数量',
            'order_id': '订单ID',
            'order_no': '订单号',
            'inbound_id': '入库ID',
            'inbound_record_id': '入库记录ID',
            'customer_id': '客户ID',
            'user_id': '用户ID',
            'category': '类别',
            'status': '状态',
            'create_time': '创建时间',
            'update_time': '更新时间',
            'create_date': '创建日期',
            'remark': '备注',
            'description': '描述',
            'code': '编码',
        }

        for table_name, table_info in tables.items():
            table_comment = table_info["comment"]
            columns = table_info["columns"]
            table_name_lower = table_name.lower()

            # Infer table semantic from name
            table_semantic = ""
            if 'inbound' in table_name_lower or 'purchase' in table_name_lower:
                table_semantic = " [入库相关]"
            elif 'order' in table_name_lower or 'sale' in table_name_lower:
                table_semantic = " [订单相关]"
            elif 'product' in table_name_lower or 'goods' in table_name_lower:
                table_semantic = " [产品相关]"
            elif 'detail' in table_name_lower:
                table_semantic = " [明细表]"

            # Build column list with semantic hints
            col_strs = []
            for col in columns:
                col_name = col["column_name"]
                col_comment = col["comment"]
                col_name_lower = col_name.lower()
                is_fk = col_name.endswith('_id') or col_name.endswith('_no')

                # Get semantic hint for column
                col_semantic = ""
                for pattern, hint in semantic_map.items():
                    if pattern in col_name_lower:
                        col_semantic = f" ({hint})"
                        break

                # Format column entry
                if is_fk:
                    # Try to determine what this FK references
                    ref_hint = ""
                    if 'order' in col_name_lower:
                        ref_hint = " -> 关联订单表"
                    elif 'inbound' in col_name_lower:
                        ref_hint = " -> 关联入库表"
                    elif 'product' in col_name_lower:
                        ref_hint = " -> 关联产品表"
                    elif 'customer' in col_name_lower or 'user' in col_name_lower:
                        ref_hint = " -> 关联用户/客户表"

                    if col_comment:
                        col_strs.append(f"  - {col_name} ({col['data_type']}): {col_comment}{col_semantic} [外键{ref_hint}]")
                    else:
                        col_strs.append(f"  - {col_name} ({col['data_type']}){col_semantic} [外键{ref_hint}]")
                    fk_hints.append(f"    {table_name}.{col_name}{ref_hint}")
                elif col_comment:
                    col_strs.append(f"  - {col_name} ({col['data_type']}): {col_comment}{col_semantic}")
                else:
                    col_strs.append(f"  - {col_name} ({col['data_type']}){col_semantic}")

            # Table entry with comment and semantic
            if table_comment:
                schema_parts.append(f"- {table_name}{table_semantic}: {table_comment}\n" + "\n".join(col_strs))
            else:
                schema_parts.append(f"- {table_name}{table_semantic}\n" + "\n".join(col_strs))

        schema_text = "\n\n".join(schema_parts) if schema_parts else "（暂无表结构信息）"

        # Add foreign key hints if any
        if fk_hints:
            schema_text += "\n\n【表关联说明】"
            schema_text += "\n" + "\n".join(fk_hints)
            schema_text += "\n\n重要提示："
            schema_text += "\n- 明细表（如 xxx_detail）通常包含主表的汇总字段（如 total_amount）"
            schema_text += "\n- 如 inbound_record 是主表（包含总金额），inbound_record_detail 是明细表（包含产品信息）"
            schema_text += "\n- 查询多个表时必须使用 JOIN，通过外键关联"

        return schema_text

    def _get_terminology_context(
        self,
        db: Session,
        datasource_id: Optional[int] = None,
    ) -> str:
        """Get terminology context for prompt enhancement."""
        from server.models.terminology import Terminology

        query = db.query(Terminology).filter(
            Terminology.enabled == True,
            (Terminology.datasource_id == datasource_id) |
            (Terminology.datasource_id == None)
        )

        terms = query.all()
        if not terms:
            return "（无特殊术语）"

        term_parts = []
        for t in terms:
            synonyms = t.synonyms or t.name
            term_parts.append(f"- {t.name}: {synonyms}")

        return "\n".join(term_parts) if term_parts else "（无特殊术语）"

    def _get_training_examples(
        self,
        db: Session,
        datasource_id: Optional[int] = None,
        limit: int = 3,
    ) -> str:
        """Get training examples for few-shot learning."""
        from server.models.data_training import DataTraining

        query = db.query(DataTraining).filter(
            DataTraining.enabled == True,
            (DataTraining.datasource_id == datasource_id) |
            (DataTraining.datasource_id == None)
        )

        examples = query.limit(limit).all()
        if not examples:
            return ""

        example_parts = ["【参考示例】"]
        for ex in examples:
            example_parts.append(f"问题: {ex.question}")
            example_parts.append(f"SQL: {ex.sql}")
            example_parts.append("")

        return "\n".join(example_parts)

    def _build_prompt(
        self,
        user_query: str,
        schema_context: str,
        terminology_context: str,
        training_examples: str,
    ) -> str:
        """Build the complete prompt with all context."""
        prompt = BASE_SQL_GEN_PROMPT.format(
            schema_info=schema_context,
            terminology_info=terminology_context,
            user_query=user_query,
        )

        if training_examples:
            prompt = training_examples + "\n\n" + prompt

        return prompt

    def generate(
        self,
        user_query: str,
        datasource_id: int,
        db: Optional[Session] = None,
    ) -> dict:
        """Generate SQL from natural language query.

        Args:
            user_query: Natural language query from user
            datasource_id: Target datasource ID
            db: Database session (optional)

        Returns:
            dict with keys: sql (str), used_tables (list), success (bool), error (str, optional)
        """
        close_db = False
        if db is None:
            db = get_db_session()
            close_db = True

        try:
            # Build context
            schema_context = self._build_schema_context(db, datasource_id)
            terminology_context = self._get_terminology_context(db, datasource_id)
            training_examples = self._get_training_examples(db, datasource_id)

            # Build prompt
            prompt = self._build_prompt(
                user_query,
                schema_context,
                terminology_context,
                training_examples,
            )

            # Generate SQL
            print(f"[DEBUG] Prompt being sent to LLM:\n{prompt[:500]}...", flush=True)
            response = self.llm.invoke(prompt)
            generated_sql = response.content.strip()

            print(f"[DEBUG] Generated SQL (raw): {generated_sql[:500]}", flush=True)

            # Extract SQL from markdown code blocks
            generated_sql = self._extract_sql_from_response(generated_sql)

            print(f"[DEBUG] Generated SQL (extracted): {generated_sql[:500]}", flush=True)

            # If no valid SQL extracted, return error
            if not generated_sql or not generated_sql.strip().upper().startswith('SELECT'):
                return {
                    "success": False,
                    "sql": "",
                    "used_tables": [],
                    "error": "无法从响应中提取有效的 SQL 语句。请检查表结构是否已配置。",
                }

            # Extract used tables
            used_tables = self._extract_tables(generated_sql)

            return {
                "success": True,
                "sql": generated_sql,
                "used_tables": used_tables,
            }

        except Exception as e:
            return {
                "success": False,
                "sql": "",
                "used_tables": [],
                "error": str(e),
            }
        finally:
            if close_db:
                db.close()

    def _extract_tables(self, sql: str) -> list[str]:
        """Extract table names from SQL."""
        import re

        tables = set()
        patterns = [
            r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        sql_upper = sql.upper()
        for pattern in patterns:
            matches = re.findall(pattern, sql_upper)
            tables.update([m.lower() for m in matches])

        return list(tables)

    def _extract_sql_from_response(self, response: str) -> str:
        """Extract SQL from LLM response, handling markdown formatting and thinking."""
        import re

        # Remove thinking blocks more aggressively (<think>...亡, <thought>...</thought>, etc.)
        response = re.sub(r'<think>.*?亡', '', response, flags=re.DOTALL)
        response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'<thought>.*?</thought>', '', response, flags=re.DOTALL | re.IGNORECASE)
        response = re.sub(r'分析与解答：.*?SQL语句：', '', response, flags=re.DOTALL)

        # Try to find SQL in code blocks first
        sql_block_pattern = r'```(?:sql)?\s*\n?(.*?)\n?```'
        matches = re.findall(sql_block_pattern, response, re.DOTALL | re.IGNORECASE)
        if matches:
            for match in matches:
                sql = match.strip()
                # Clean up the SQL - remove leading/trailing non-SQL content
                sql = re.sub(r'^[^S]*', '', sql, flags=re.IGNORECASE)  # Remove anything before first SELECT
                if sql.upper().startswith('SELECT'):
                    # Remove any trailing explanations or notes
                    sql = re.split(r'(?: Lindsay|```|\n\n|\n[A-Z]+：|$)', sql, flags=re.IGNORECASE)[0].strip()
                    if len(sql) > 10:  # Valid SQL should be at least 10 chars
                        return sql

        # If no code block, try to extract SQL from multi-line text
        # Look for SELECT statement that might span multiple lines
        select_pattern = r'(SELECT\s+.*?(?:LIMIT\s+\d+)?)\s*(?:;|$|\n\n|\n[A-Z]{2,}：|\Z)'
        matches = re.findall(select_pattern, response, re.IGNORECASE | re.DOTALL)
        if matches:
            for match in matches:
                sql = match.strip()
                if sql.upper().startswith('SELECT') and len(sql) > 20:
                    return sql

        # Last resort: find any SELECT statement and clean it up
        lines = response.split('\n')
        sql_lines = []
        in_sql = False
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SELECT'):
                in_sql = True
                sql_lines = [line]
            elif in_sql:
                # Check if this line continues the SQL or starts something new
                upper_line = line.upper()
                if upper_line.startswith('WHERE') or upper_line.startswith('FROM') or \
                   upper_line.startswith('JOIN') or upper_line.startswith('LEFT') or \
                   upper_line.startswith('INNER') or upper_line.startswith('GROUP') or \
                   upper_line.startswith('ORDER') or upper_line.startswith('AND') or \
                   upper_line.startswith('ON ') or upper_line.startswith('SET ') or \
                   upper_line.startswith('LIMIT'):
                    sql_lines.append(line)
                elif line and not line.startswith('[') and not line.startswith('(') and \
                     len(line) > 5 and not line.endswith('：'):
                    # This might be a continuation or explanation, include it
                    if not re.match(r'^[A-Z]{2,}：', line):  # Not a header like "分析："
                        sql_lines.append(line)
                else:
                    break  # Probably hit non-SQL content

        if sql_lines:
            # Clean up the combined SQL
            sql = ' '.join(sql_lines)
            sql = re.sub(r'[;\'"].*$', '', sql).strip()  # Remove trailing chars
            sql = re.sub(r'\n.*$', '', sql).strip()  # Remove anything after newline
            if sql.upper().startswith('SELECT') and len(sql) > 20:
                return sql

        # If still nothing, return empty to signal failure
        return ""


def get_sql_generator_with_default_model() -> Optional[SQLGenerator]:
    """Get SQL generator using the default configured AI model."""
    from server.models.ai_model import AIModel

    db = get_db_session()
    try:
        # Try to get default model
        model_config = db.query(AIModel).filter(
            AIModel.is_default == True,
            AIModel.enabled == True
        ).first()

        if not model_config:
            # Use first enabled model
            model_config = db.query(AIModel).filter(
                AIModel.enabled == True
            ).first()

        if not model_config:
            return None

        extra_config = {}
        if model_config.config_list:
            try:
                extra_config = json.loads(model_config.config_list)
            except json.JSONDecodeError:
                pass

        return SQLGenerator(
            llm_model=model_config.base_model,
            temperature=extra_config.get("temperature", 0.0),
            api_key=model_config.api_key_encrypted,
            api_domain=model_config.api_domain,
            supplier=model_config.supplier,
        )
    finally:
        db.close()


# Singleton instance
_generator_instance: Optional[SQLGenerator] = None


def get_sql_generator() -> SQLGenerator:
    """Get or create SQL generator singleton."""
    global _generator_instance
    if _generator_instance is None:
        # Try to use default configured model
        _generator_instance = get_sql_generator_with_default_model()
        if _generator_instance is None:
            # Fallback to default
            _generator_instance = SQLGenerator()
    return _generator_instance
