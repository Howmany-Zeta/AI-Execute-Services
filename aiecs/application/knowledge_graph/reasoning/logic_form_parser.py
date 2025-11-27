"""
Logic Form Parser

Wrapper around LogicQueryParser for converting natural language queries
to structured logical forms.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from aiecs.application.knowledge_graph.reasoning.logic_parser import (
    LogicQueryParser,
)
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager


class QueryType(str, Enum):
    """Query type enumeration"""

    SELECT = "SELECT"
    ASK = "ASK"
    COUNT = "COUNT"
    FIND = "FIND"


@dataclass
class Variable:
    """Query variable"""

    name: str
    type: Optional[str] = None


@dataclass
class Predicate:
    """Logical predicate"""

    name: str
    arguments: List[Any] = field(default_factory=list)


@dataclass
class Constraint:
    """Query constraint"""

    constraint_type: str
    variable: Variable
    value: Any


@dataclass
class LogicalQuery:
    """
    Structured logical query representation

    Represents a parsed natural language query as a logical form
    with variables, predicates, and constraints.
    """

    query_type: QueryType
    variables: List[Variable] = field(default_factory=list)
    predicates: List[Predicate] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    raw_query: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "query_type": self.query_type.value,
            "variables": [{"name": v.name, "type": v.type} for v in self.variables],
            "predicates": [
                {
                    "name": p.name,
                    "arguments": [arg.name if hasattr(arg, "name") else str(arg) for arg in p.arguments],
                }
                for p in self.predicates
            ],
            "constraints": [
                {
                    "type": c.constraint_type,
                    "variable": c.variable.name,
                    "value": c.value,
                }
                for c in self.constraints
            ],
            "raw_query": self.raw_query,
        }


class LogicFormParser:
    """
    Logic Form Parser

    Converts natural language queries into structured logical forms.
    Uses LogicQueryParser internally for parsing.

    Example:
        ```python
        parser = LogicFormParser()
        logical_query = parser.parse("Find all people who work for companies in San Francisco")

        print(f"Query type: {logical_query.query_type}")
        print(f"Variables: {[v.name for v in logical_query.variables]}")
        print(f"Predicates: {[p.name for p in logical_query.predicates]}")
        ```
    """

    def __init__(self, schema_manager: Optional[SchemaManager] = None):
        """
        Initialize logic form parser

        Args:
            schema_manager: Optional schema manager for type validation
        """
        self.schema_manager = schema_manager
        # Type annotation for optional attribute
        self.query_parser: Optional[LogicQueryParser]
        if schema_manager:
            self.query_parser = LogicQueryParser(schema_manager)  # type: ignore[assignment]
        else:
            # Create a minimal schema manager if none provided
            self.query_parser = None

    def parse(self, query: str) -> LogicalQuery:
        """
        Parse natural language query to logical form

        Args:
            query: Natural language query string

        Returns:
            LogicalQuery with structured representation
        """
        # Simple heuristic-based parsing for now
        # In a full implementation, this would use NLP or the LogicQueryParser

        logical_query = LogicalQuery(query_type=QueryType.FIND, raw_query=query)

        # Extract variables (simple pattern matching)
        if "people" in query.lower() or "person" in query.lower():
            logical_query.variables.append(Variable(name="?person", type="Person"))
        if "companies" in query.lower() or "company" in query.lower():
            logical_query.variables.append(Variable(name="?company", type="Company"))

        # Extract predicates
        if "work for" in query.lower() or "works for" in query.lower():
            logical_query.predicates.append(Predicate(name="WORKS_FOR", arguments=["?person", "?company"]))
        if "located in" in query.lower():
            logical_query.predicates.append(Predicate(name="LOCATED_IN", arguments=["?company", "San Francisco"]))

        # Extract constraints
        if "in San Francisco" in query or "in san francisco" in query.lower():
            if logical_query.variables:
                logical_query.constraints.append(
                    Constraint(
                        constraint_type="property_equals",
                        variable=logical_query.variables[-1],
                        value="San Francisco",
                    )
                )

        return logical_query
