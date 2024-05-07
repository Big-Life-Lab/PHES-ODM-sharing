from dataclasses import dataclass
from typing import Dict

from odm_sharing.private.rules import RuleId


SqlQuery = str


@dataclass(frozen=True)
class Query:
    data_sql: SqlQuery
    rule_count_sqls: Dict[RuleId, SqlQuery]
    column_sql: SqlQuery
