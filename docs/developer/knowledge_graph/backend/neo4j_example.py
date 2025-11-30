"""
Neo4j Graph Store Adapter (Example Implementation)

This is a reference implementation showing how to create a custom backend.
It implements only Tier 1 methods, so Tier 2 methods work automatically.

Note: This is an EXAMPLE, not a built-in implementation.
To use it, you need to install neo4j: `pip install neo4j`
"""

from typing import List, Optional
from contextlib import asynccontextmanager

from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class Neo4jGraphStore(GraphStore):
    """
    Neo4j backend adapter (minimal implementation)
    
    This is a reference implementation showing how to create a custom backend.
    It implements only Tier 1 methods, so Tier 2 methods work automatically.
    
    Requirements:
        pip install neo4j
    
    Example:
        ```python
        store = Neo4jGraphStore(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        await store.initialize()
        
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)
        
        # Tier 2 methods work automatically!
        paths = await store.find_paths("e1", "e2", max_depth=3)
        ```
    """
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """
        Initialize Neo4j adapter
        
        Args:
            uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            user: Neo4j username
            password: Neo4j password
            database: Neo4j database name (default: "neo4j")
        """
        super().__init__()
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Neo4j connection"""
        try:
            from neo4j import AsyncGraphDatabase
        except ImportError:
            raise ImportError(
                "neo4j package not installed. Install it with: pip install neo4j"
            )
        
        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        
        # Verify connection
        async with self.driver.session(database=self.database) as session:
            result = await session.run("RETURN 1 as test")
            await result.single()
        
        self._initialized = True
    
    async def close(self) -> None:
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
        self._initialized = False
    
    @asynccontextmanager
    async def transaction(self):
        """Transaction context manager"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            async with session.begin_transaction() as tx:
                yield tx
    
    async def add_entity(self, entity: Entity) -> None:
        """Add entity to Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            # Check if exists
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=entity.id
            )
            if await result.single():
                raise ValueError(f"Entity {entity.id} already exists")
            
            # Create node with label from entity_type
            await session.run(
                f"""
                CREATE (n:{entity.entity_type} {{
                    id: $id,
                    entity_type: $type,
                    properties: $props
                }})
                """,
                id=entity.id,
                type=entity.entity_type,
                props=entity.properties
            )
            await session.commit()
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                "MATCH (n {id: $id}) RETURN n",
                id=entity_id
            )
            record = await result.single()
            if not record:
                return None
            
            node = record["n"]
            return Entity(
                id=node["id"],
                entity_type=node["entity_type"],
                properties=node["properties"]
            )
    
    async def update_entity(self, entity: Entity) -> None:
        """Update entity in Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (n {id: $id})
                SET n.entity_type = $type,
                    n.properties = $props
                RETURN n
                """,
                id=entity.id,
                type=entity.entity_type,
                props=entity.properties
            )
            if not await result.single():
                raise ValueError(f"Entity {entity.id} not found")
            await session.commit()
    
    async def delete_entity(self, entity_id: str) -> None:
        """Delete entity from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                "MATCH (n {id: $id}) DELETE n RETURN count(n) as deleted",
                id=entity_id
            )
            record = await result.single()
            if record["deleted"] == 0:
                raise ValueError(f"Entity {entity_id} not found")
            await session.commit()
    
    async def add_relation(self, relation: Relation) -> None:
        """Add relation to Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        # Verify entities exist
        source = await self.get_entity(relation.source_id)
        target = await self.get_entity(relation.target_id)
        if not source or not target:
            raise ValueError("Source or target entity not found")
        
        async with self.driver.session(database=self.database) as session:
            await session.run(
                f"""
                MATCH (a {{id: $source}}), (b {{id: $target}})
                CREATE (a)-[r:{relation.relation_type} {{
                    id: $id,
                    relation_type: $type,
                    properties: $props,
                    weight: $weight
                }}]->(b)
                RETURN r
                """,
                source=relation.source_id,
                target=relation.target_id,
                id=relation.id,
                type=relation.relation_type,
                props=relation.properties,
                weight=relation.weight
            )
            await session.commit()
    
    async def get_relation(self, relation_id: str) -> Optional[Relation]:
        """Get relation from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH ()-[r {id: $id}]-()
                RETURN r, 
                       startNode(r).id as source_id,
                       endNode(r).id as target_id
                """,
                id=relation_id
            )
            record = await result.single()
            if not record:
                return None
            
            rel = record["r"]
            return Relation(
                id=rel["id"],
                source_id=record["source_id"],
                target_id=record["target_id"],
                relation_type=rel["relation_type"],
                properties=rel["properties"],
                weight=rel.get("weight", 1.0)
            )
    
    async def delete_relation(self, relation_id: str) -> None:
        """Delete relation from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                "MATCH ()-[r {id: $id}]-() DELETE r RETURN count(r) as deleted",
                id=relation_id
            )
            record = await result.single()
            if record["deleted"] == 0:
                raise ValueError(f"Relation {relation_id} not found")
            await session.commit()
    
    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing"
    ) -> List[Entity]:
        """Get neighbors from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            if direction == "outgoing":
                query = "MATCH (n {id: $id})-[r]->(m) RETURN DISTINCT m"
            elif direction == "incoming":
                query = "MATCH (n {id: $id})<-[r]-(m) RETURN DISTINCT m"
            else:  # both
                query = "MATCH (n {id: $id})-[r]-(m) RETURN DISTINCT m"
            
            if relation_type:
                query = query.replace("RETURN", "WHERE r.relation_type = $type RETURN")
            
            params = {"id": entity_id}
            if relation_type:
                params["type"] = relation_type
            
            result = await session.run(query, **params)
            entities = []
            async for record in result:
                node = record["m"]
                entities.append(Entity(
                    id=node["id"],
                    entity_type=node["entity_type"],
                    properties=node["properties"]
                ))
            return entities
    
    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Get all entities from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            if entity_type:
                query = f"MATCH (n:{entity_type}) RETURN n"
            else:
                query = "MATCH (n) WHERE n.id IS NOT NULL RETURN n"
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = await session.run(query)
            entities = []
            async for record in result:
                node = record["n"]
                entities.append(Entity(
                    id=node["id"],
                    entity_type=node["entity_type"],
                    properties=node["properties"]
                ))
            return entities
    
    async def get_stats(self) -> dict:
        """Get graph statistics from Neo4j"""
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            entity_count = await session.run("MATCH (n) WHERE n.id IS NOT NULL RETURN count(n) as count")
            relation_count = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            
            entity_record = await entity_count.single()
            relation_record = await relation_count.single()
            
            return {
                "entity_count": entity_record["count"] if entity_record else 0,
                "relation_count": relation_record["count"] if relation_record else 0,
                "backend": "neo4j"
            }
    
    # =========================================================================
    # Tier 2: Optional Optimizations
    # =========================================================================
    
    async def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        limit: Optional[int] = 10
    ) -> List:
        """
        Optimized path finding using Cypher shortestPath
        
        This overrides the default implementation with Neo4j-specific optimization.
        """
        from aiecs.domain.knowledge_graph.models.path import Path
        
        if not self._initialized:
            raise RuntimeError("Store not initialized")
        
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH path = shortestPath(
                    (a {id: $source})-[*1..$max_depth]-(b {id: $target})
                )
                RETURN path
                LIMIT $limit
                """,
                source=source_id,
                target=target_id,
                max_depth=max_depth,
                limit=limit or 10
            )
            
            paths = []
            async for record in result:
                cypher_path = record["path"]
                # Convert Cypher path to Path object
                nodes = []
                edges = []
                
                for node in cypher_path.nodes:
                    nodes.append(Entity(
                        id=node["id"],
                        entity_type=node["entity_type"],
                        properties=node["properties"]
                    ))
                
                for rel in cypher_path.relationships:
                    edges.append(Relation(
                        id=rel["id"],
                        source_id=rel.start_node["id"],
                        target_id=rel.end_node["id"],
                        relation_type=rel["relation_type"],
                        properties=rel["properties"],
                        weight=rel.get("weight", 1.0)
                    ))
                
                if nodes and edges:
                    paths.append(Path(nodes=nodes, edges=edges))
            
            return paths

