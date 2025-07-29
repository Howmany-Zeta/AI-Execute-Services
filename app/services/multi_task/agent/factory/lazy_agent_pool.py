"""
Lazy Agent Pool

Provides on-demand agent creation with intelligent caching for the LangChain engine.
Supports lazy creation, intelligent caching, and automatic cleanup of agents.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class LazyAgentPool:
    """
    Lazy Agent Pool - On-demand creation with intelligent caching.

    This pool manages agents with lazy creation, intelligent caching, and automatic cleanup.
    Agents are created on-demand and cached for reuse to optimize performance.
    """

    def __init__(self, agent_manager, max_pool_size: int = 10, idle_timeout: int = 300):
        """
        Initialize the lazy agent pool.

        Args:
            agent_manager: DynamicAgentManager instance for creating agents
            max_pool_size: Maximum number of agents to keep in pool per role
            idle_timeout: Timeout in seconds before idle agents are cleaned up
        """
        self.agent_manager = agent_manager
        self.pool_cache: Dict[str, List[str]] = {}  # role -> [agent_ids]
        self.agent_usage: Dict[str, datetime] = {}  # agent_id -> last_used
        self.max_pool_size = max_pool_size
        self.idle_timeout = idle_timeout

        # Pool statistics
        self.stats = {
            'total_created': 0,
            'total_reused': 0,
            'total_destroyed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

        logger.info(f"LazyAgentPool initialized with max_pool_size={max_pool_size}, idle_timeout={idle_timeout}s")

    async def get_or_create_agent(
        self,
        role: str,
        context: Dict[str, Any],
        tools: List = None
    ) -> str:
        """
        Get an existing agent from pool or create a new one (lazy creation).

        Args:
            role: Agent role identifier
            context: Execution context for agent creation
            tools: Optional list of tools to assign to the agent

        Returns:
            Agent ID of the retrieved or created agent
        """
        # Try to get an idle agent from the pool first
        if role in self.pool_cache and self.pool_cache[role]:
            agent_id = self.pool_cache[role].pop(0)
            self.agent_usage[agent_id] = datetime.utcnow()
            self.stats['total_reused'] += 1
            self.stats['cache_hits'] += 1
            logger.debug(f"Reused agent from pool: {agent_id} for role: {role}")
            return agent_id

        # No available agent in pool, create a new one
        self.stats['cache_misses'] += 1
        agent_id = await self.agent_manager.create_agent_on_demand(
            role=role,
            context=context,
            tools=tools
        )

        self.agent_usage[agent_id] = datetime.utcnow()
        self.stats['total_created'] += 1
        logger.debug(f"Created new agent: {agent_id} for role: {role}")
        return agent_id

    async def return_agent_to_pool(self, agent_id: str, role: str):
        """
        Return an agent to the pool for reuse.

        Args:
            agent_id: ID of the agent to return
            role: Role of the agent for proper categorization
        """
        if role not in self.pool_cache:
            self.pool_cache[role] = []

        # Check if pool has space for this role
        if len(self.pool_cache[role]) < self.max_pool_size:
            self.pool_cache[role].append(agent_id)
            self.agent_usage[agent_id] = datetime.utcnow()
            logger.debug(f"Returned agent to pool: {agent_id} for role: {role}")
        else:
            # Pool is full, destroy the agent
            await self.agent_manager.destroy_agent(agent_id)
            if agent_id in self.agent_usage:
                del self.agent_usage[agent_id]
            self.stats['total_destroyed'] += 1
            logger.debug(f"Pool full, destroyed agent: {agent_id} for role: {role}")

    async def cleanup_idle_agents(self):
        """
        Clean up agents that have been idle for longer than the timeout.
        This method should be called periodically to maintain pool health.
        """
        current_time = datetime.utcnow()
        agents_to_remove = []

        # Find agents that have exceeded idle timeout
        for agent_id, last_used in self.agent_usage.items():
            if (current_time - last_used).total_seconds() > self.idle_timeout:
                agents_to_remove.append(agent_id)

        # Remove idle agents
        for agent_id in agents_to_remove:
            await self.agent_manager.destroy_agent(agent_id)
            del self.agent_usage[agent_id]

            # Remove from pool cache
            for role_agents in self.pool_cache.values():
                if agent_id in role_agents:
                    role_agents.remove(agent_id)

            self.stats['total_destroyed'] += 1

        if agents_to_remove:
            logger.info(f"Cleaned up {len(agents_to_remove)} idle agents")

    async def get_pool_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the agent pool.

        Returns:
            Dictionary containing pool statistics and metrics
        """
        current_time = datetime.utcnow()

        # Calculate pool utilization by role
        role_utilization = {}
        total_pooled_agents = 0

        for role, agents in self.pool_cache.items():
            role_utilization[role] = {
                'pooled_count': len(agents),
                'max_capacity': self.max_pool_size,
                'utilization_percent': (len(agents) / self.max_pool_size) * 100
            }
            total_pooled_agents += len(agents)

        # Calculate average idle time
        idle_times = []
        for agent_id, last_used in self.agent_usage.items():
            idle_time = (current_time - last_used).total_seconds()
            idle_times.append(idle_time)

        avg_idle_time = sum(idle_times) / len(idle_times) if idle_times else 0

        return {
            'pool_config': {
                'max_pool_size': self.max_pool_size,
                'idle_timeout': self.idle_timeout
            },
            'current_state': {
                'total_pooled_agents': total_pooled_agents,
                'total_tracked_agents': len(self.agent_usage),
                'roles_in_pool': len(self.pool_cache),
                'average_idle_time_seconds': avg_idle_time
            },
            'role_utilization': role_utilization,
            'lifetime_stats': self.stats.copy(),
            'efficiency_metrics': {
                'cache_hit_rate': (self.stats['cache_hits'] /
                                 (self.stats['cache_hits'] + self.stats['cache_misses'])) * 100
                                 if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0,
                'reuse_rate': (self.stats['total_reused'] /
                              (self.stats['total_created'] + self.stats['total_reused'])) * 100
                              if (self.stats['total_created'] + self.stats['total_reused']) > 0 else 0
            }
        }

    async def force_cleanup_all(self):
        """
        Force cleanup of all agents in the pool.
        This should be used during shutdown or emergency cleanup.
        """
        logger.info("Force cleanup of all agents in pool")

        # Destroy all tracked agents
        for agent_id in list(self.agent_usage.keys()):
            try:
                await self.agent_manager.destroy_agent(agent_id)
                self.stats['total_destroyed'] += 1
            except Exception as e:
                logger.error(f"Error destroying agent {agent_id} during force cleanup: {e}")

        # Clear all data structures
        self.pool_cache.clear()
        self.agent_usage.clear()

        logger.info("Force cleanup completed")

    async def resize_pool(self, new_max_size: int):
        """
        Resize the maximum pool size and adjust current pools accordingly.

        Args:
            new_max_size: New maximum pool size per role
        """
        old_size = self.max_pool_size
        self.max_pool_size = new_max_size

        logger.info(f"Resizing pool from {old_size} to {new_max_size}")

        # If reducing size, remove excess agents from each role
        if new_max_size < old_size:
            for role, agents in self.pool_cache.items():
                while len(agents) > new_max_size:
                    agent_id = agents.pop()
                    await self.agent_manager.destroy_agent(agent_id)
                    if agent_id in self.agent_usage:
                        del self.agent_usage[agent_id]
                    self.stats['total_destroyed'] += 1

    def get_agents_by_role(self, role: str) -> List[str]:
        """
        Get list of agent IDs currently pooled for a specific role.

        Args:
            role: Role to query

        Returns:
            List of agent IDs for the specified role
        """
        return self.pool_cache.get(role, []).copy()

    def is_agent_pooled(self, agent_id: str) -> bool:
        """
        Check if an agent is currently in the pool.

        Args:
            agent_id: Agent ID to check

        Returns:
            True if agent is in pool, False otherwise
        """
        for agents in self.pool_cache.values():
            if agent_id in agents:
                return True
        return False

    async def warmup_pool(self, role_configs: List[Dict[str, Any]]):
        """
        Pre-warm the pool by creating agents for specified roles.

        Args:
            role_configs: List of role configurations for pre-warming
                         Each config should have 'role', 'count', 'context', 'tools'
        """
        logger.info(f"Warming up pool with {len(role_configs)} role configurations")

        for config in role_configs:
            role = config['role']
            count = config.get('count', 1)
            context = config.get('context', {})
            tools = config.get('tools', [])

            for _ in range(count):
                try:
                    agent_id = await self.get_or_create_agent(role, context, tools)
                    await self.return_agent_to_pool(agent_id, role)
                except Exception as e:
                    logger.error(f"Error warming up agent for role {role}: {e}")

        logger.info("Pool warmup completed")
