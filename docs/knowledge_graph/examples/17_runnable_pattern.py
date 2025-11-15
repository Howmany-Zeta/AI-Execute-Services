"""
Example: Using the Runnable Pattern

This example demonstrates how to use the Runnable pattern to build
robust async components with automatic retry, circuit breaker, and
lifecycle management.
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List
from aiecs.common.knowledge_graph import Runnable, RunnableConfig


# Example 1: Simple Data Processor
# ================================

@dataclass
class ProcessorConfig(RunnableConfig):
    """Configuration for data processor"""
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0


class DataProcessor(Runnable[ProcessorConfig, Dict[str, Any]]):
    """Simple data processor with retry logic"""
    
    async def _setup(self) -> None:
        """Initialize processor"""
        print("Setting up data processor...")
        self.processed_items = []
    
    async def _execute(self, items: List[str]) -> Dict[str, Any]:
        """Process items in batches"""
        print(f"Processing {len(items)} items...")
        
        # Simulate processing
        for i in range(0, len(items), self.config.batch_size):
            batch = items[i:i + self.config.batch_size]
            processed = [item.upper() for item in batch]
            self.processed_items.extend(processed)
            await asyncio.sleep(0.1)  # Simulate work
        
        return {
            "total_processed": len(self.processed_items),
            "items": self.processed_items
        }
    
    async def _teardown(self) -> None:
        """Cleanup"""
        print("Cleaning up data processor...")
        self.processed_items.clear()


# Example 2: API Client with Circuit Breaker
# ==========================================

@dataclass
class APIConfig(RunnableConfig):
    """Configuration for API client"""
    base_url: str = "https://api.example.com"
    max_retries: int = 5
    retry_delay: float = 2.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 3
    timeout: float = 30.0


class APIClient(Runnable[APIConfig, Dict[str, Any]]):
    """API client with circuit breaker and retry logic"""
    
    def __init__(self, config: APIConfig):
        super().__init__(config)
        self.request_count = 0
    
    async def _setup(self) -> None:
        """Initialize API client"""
        print(f"Connecting to {self.config.base_url}...")
        # In real implementation, create HTTP client here
        self.connected = True
    
    async def _execute(self, endpoint: str, **params) -> Dict[str, Any]:
        """Make API request"""
        self.request_count += 1
        print(f"Request #{self.request_count} to {endpoint}")
        
        # Simulate API call
        await asyncio.sleep(0.5)
        
        # Simulate occasional failures for demo
        if self.request_count % 7 == 0:
            raise RuntimeError("Simulated API error")
        
        return {
            "endpoint": endpoint,
            "params": params,
            "status": "success",
            "request_number": self.request_count
        }
    
    async def _teardown(self) -> None:
        """Cleanup API client"""
        print("Disconnecting from API...")
        self.connected = False


# Example 3: Composing Multiple Runnables
# =======================================

@dataclass
class PipelineConfig(RunnableConfig):
    """Configuration for processing pipeline"""
    processor_batch_size: int = 50
    max_retries: int = 3


class ProcessingPipeline(Runnable[PipelineConfig, Dict[str, Any]]):
    """Pipeline that composes multiple runnable components"""
    
    async def _setup(self) -> None:
        """Setup pipeline components"""
        print("Setting up processing pipeline...")
        
        # Create sub-components
        processor_config = ProcessorConfig(
            batch_size=self.config.processor_batch_size,
            max_retries=self.config.max_retries
        )
        self.processor = DataProcessor(processor_config)
        await self.processor.setup()
    
    async def _execute(self, data: List[str]) -> Dict[str, Any]:
        """Execute pipeline"""
        print(f"Running pipeline on {len(data)} items...")
        
        # Step 1: Process data
        processed = await self.processor.run(items=data)
        
        # Step 2: Additional processing
        result = {
            "input_count": len(data),
            "output_count": processed["total_processed"],
            "pipeline_metrics": self.processor.get_metrics_dict()
        }
        
        return result
    
    async def _teardown(self) -> None:
        """Cleanup pipeline"""
        print("Cleaning up pipeline...")
        await self.processor.teardown()


# Demo Functions
# ==============

async def demo_basic_usage():
    """Demo 1: Basic usage with context manager"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Usage")
    print("="*60)
    
    config = ProcessorConfig(batch_size=3)
    items = ["apple", "banana", "cherry", "date", "elderberry"]
    
    async with DataProcessor(config) as processor:
        result = await processor.run(items=items)
        print(f"\nResult: {result}")
        print(f"Metrics: {processor.get_metrics_dict()}")


async def demo_retry_logic():
    """Demo 2: Retry logic with exponential backoff"""
    print("\n" + "="*60)
    print("DEMO 2: Retry Logic")
    print("="*60)

    config = APIConfig(
        max_retries=3,
        retry_delay=0.5,
        retry_backoff=2.0,
        enable_circuit_breaker=False  # Disable for this demo
    )

    async with APIClient(config) as client:
        # Make multiple requests
        for i in range(10):
            try:
                result = await client.run(endpoint=f"/data/{i}")
                print(f"✓ Request {i}: {result['status']}")
            except Exception as e:
                print(f"✗ Request {i} failed: {e}")

            # Show retry count
            if client.metrics.retry_count > 0:
                print(f"  (Retried {client.metrics.retry_count} times)")


async def demo_circuit_breaker():
    """Demo 3: Circuit breaker pattern"""
    print("\n" + "="*60)
    print("DEMO 3: Circuit Breaker")
    print("="*60)

    config = APIConfig(
        max_retries=0,  # No retries for clearer demo
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3,
        circuit_breaker_timeout=2.0
    )

    async with APIClient(config) as client:
        # Make requests until circuit opens
        for i in range(15):
            try:
                result = await client.run(endpoint=f"/data/{i}")
                print(f"✓ Request {i}: Success")
            except RuntimeError as e:
                if "Circuit breaker is open" in str(e):
                    print(f"⚠ Request {i}: Circuit breaker is OPEN")
                    print("  Waiting for circuit to reset...")
                    await asyncio.sleep(2.5)  # Wait for timeout
                else:
                    print(f"✗ Request {i}: {e}")

            await asyncio.sleep(0.1)


async def demo_timeout():
    """Demo 4: Timeout handling"""
    print("\n" + "="*60)
    print("DEMO 4: Timeout Handling")
    print("="*60)

    @dataclass
    class SlowConfig(RunnableConfig):
        delay: float = 5.0
        timeout: float = 2.0

    class SlowComponent(Runnable[SlowConfig, str]):
        async def _setup(self) -> None:
            pass

        async def _execute(self) -> str:
            print(f"Starting slow operation ({self.config.delay}s)...")
            await asyncio.sleep(self.config.delay)
            return "completed"

        async def _teardown(self) -> None:
            pass

    config = SlowConfig(delay=5.0, timeout=2.0)

    async with SlowComponent(config) as component:
        try:
            result = await component.run()
            print(f"Result: {result}")
        except asyncio.TimeoutError:
            print("✗ Operation timed out (as expected)")


async def demo_pipeline():
    """Demo 5: Composing multiple components"""
    print("\n" + "="*60)
    print("DEMO 5: Component Composition")
    print("="*60)

    config = PipelineConfig(
        processor_batch_size=2,
        max_retries=2
    )

    data = ["alpha", "beta", "gamma", "delta", "epsilon"]

    async with ProcessingPipeline(config) as pipeline:
        result = await pipeline.run(data=data)
        print(f"\nPipeline Result:")
        print(f"  Input: {result['input_count']} items")
        print(f"  Output: {result['output_count']} items")
        print(f"  Duration: {result['pipeline_metrics']['duration_seconds']:.3f}s")


async def demo_metrics():
    """Demo 6: Metrics collection"""
    print("\n" + "="*60)
    print("DEMO 6: Metrics Collection")
    print("="*60)

    config = ProcessorConfig(batch_size=10)
    items = [f"item_{i}" for i in range(25)]

    processor = DataProcessor(config)
    await processor.setup()

    # Run multiple times and collect metrics
    for run in range(3):
        processor.reset_metrics()  # Reset for each run
        result = await processor.run(items=items)

        metrics = processor.get_metrics_dict()
        print(f"\nRun {run + 1}:")
        print(f"  Duration: {metrics['duration_seconds']:.3f}s")
        print(f"  Success: {metrics['success']}")
        print(f"  State: {metrics['state']}")

    await processor.teardown()


async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("RUNNABLE PATTERN EXAMPLES")
    print("="*60)

    # Run demos
    await demo_basic_usage()
    await demo_retry_logic()
    await demo_circuit_breaker()
    await demo_timeout()
    await demo_pipeline()
    await demo_metrics()

    print("\n" + "="*60)
    print("All demos completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())


