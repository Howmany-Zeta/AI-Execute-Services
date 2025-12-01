"""
Import Speed Optimization Utilities

Provides optimizations for structured data import:
- Parallel batch processing with worker pools
- Async I/O for file reading
- Batch size auto-tuning
- Performance metrics tracking
- Streaming import for large files
"""

import asyncio
import os
import time
import psutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Import performance metrics
    
    Tracks detailed timing and throughput information during import.
    """
    
    # Timing
    start_time: float = 0.0
    end_time: float = 0.0
    read_time_seconds: float = 0.0
    transform_time_seconds: float = 0.0
    write_time_seconds: float = 0.0
    
    # Throughput
    total_rows: int = 0
    rows_per_second: float = 0.0
    
    # Memory
    peak_memory_mb: float = 0.0
    initial_memory_mb: float = 0.0
    
    # Batch info
    batch_count: int = 0
    avg_batch_time_seconds: float = 0.0
    
    # Parallelism
    worker_count: int = 1
    parallel_speedup: float = 1.0
    
    def calculate_throughput(self) -> None:
        """Calculate derived metrics after import completes"""
        duration = self.end_time - self.start_time
        if duration > 0:
            self.rows_per_second = self.total_rows / duration
        if self.batch_count > 0:
            total_batch_time = self.read_time_seconds + self.transform_time_seconds + self.write_time_seconds
            self.avg_batch_time_seconds = total_batch_time / self.batch_count
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary dictionary for logging/reporting"""
        duration = self.end_time - self.start_time
        return {
            "total_rows": self.total_rows,
            "duration_seconds": round(duration, 2),
            "rows_per_second": round(self.rows_per_second, 1),
            "read_time_seconds": round(self.read_time_seconds, 2),
            "transform_time_seconds": round(self.transform_time_seconds, 2),
            "write_time_seconds": round(self.write_time_seconds, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 1),
            "batch_count": self.batch_count,
            "worker_count": self.worker_count,
        }


class BatchSizeOptimizer:
    """
    Auto-tunes batch size based on system resources and data characteristics.
    
    Factors considered:
    - Available memory
    - Number of columns/properties
    - Data type complexity
    - Historical performance
    """
    
    # Memory thresholds
    MIN_BATCH_SIZE = 50
    MAX_BATCH_SIZE = 10000
    DEFAULT_BATCH_SIZE = 1000
    
    # Memory allocation per row (estimated)
    BASE_MEMORY_PER_ROW_BYTES = 1024  # 1KB base
    MEMORY_PER_COLUMN_BYTES = 100  # 100 bytes per column
    
    def __init__(self, target_memory_percent: float = 0.25):
        """
        Initialize batch size optimizer
        
        Args:
            target_memory_percent: Target percentage of available memory to use (0-1)
        """
        self.target_memory_percent = target_memory_percent
        self._batch_times: List[float] = []
        self._current_batch_size = self.DEFAULT_BATCH_SIZE
    
    def estimate_batch_size(
        self,
        column_count: int,
        sample_row_size_bytes: Optional[int] = None,
    ) -> int:
        """
        Estimate optimal batch size based on system resources.
        
        Args:
            column_count: Number of columns in the data
            sample_row_size_bytes: Optional measured row size
            
        Returns:
            Recommended batch size
        """
        try:
            available_memory = psutil.virtual_memory().available
        except Exception:
            # Fallback if psutil fails
            return self.DEFAULT_BATCH_SIZE
        
        # Calculate target memory for batches
        target_memory = available_memory * self.target_memory_percent
        
        # Estimate memory per row
        if sample_row_size_bytes:
            memory_per_row = sample_row_size_bytes
        else:
            memory_per_row = self.BASE_MEMORY_PER_ROW_BYTES + (column_count * self.MEMORY_PER_COLUMN_BYTES)
        
        # Calculate batch size
        batch_size = int(target_memory / memory_per_row)
        
        # Clamp to reasonable range
        batch_size = max(self.MIN_BATCH_SIZE, min(batch_size, self.MAX_BATCH_SIZE))
        
        self._current_batch_size = batch_size
        logger.debug(f"Estimated batch size: {batch_size} (columns={column_count}, memory_per_row={memory_per_row})")

        return batch_size

    def record_batch_time(self, batch_time: float, rows_processed: int) -> None:
        """
        Record batch processing time for adaptive tuning.

        Args:
            batch_time: Time to process the batch in seconds
            rows_processed: Number of rows processed in the batch
        """
        self._batch_times.append(batch_time / max(rows_processed, 1))

    def adjust_batch_size(self) -> int:
        """
        Adjust batch size based on historical performance.

        Returns:
            Adjusted batch size
        """
        if len(self._batch_times) < 3:
            return self._current_batch_size

        # Calculate average time per row
        recent_times = self._batch_times[-5:]
        avg_time_per_row = sum(recent_times) / len(recent_times)

        # If processing is fast, increase batch size
        if avg_time_per_row < 0.001:  # < 1ms per row
            self._current_batch_size = min(
                self._current_batch_size * 2,
                self.MAX_BATCH_SIZE
            )
        # If processing is slow, decrease batch size
        elif avg_time_per_row > 0.01:  # > 10ms per row
            self._current_batch_size = max(
                self._current_batch_size // 2,
                self.MIN_BATCH_SIZE
            )

        return self._current_batch_size


class ParallelBatchProcessor:
    """
    Processes batches in parallel using a worker pool.

    Uses ThreadPoolExecutor for I/O-bound work (default) or
    ProcessPoolExecutor for CPU-bound work.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        use_processes: bool = False,
    ):
        """
        Initialize parallel batch processor.

        Args:
            max_workers: Maximum number of workers. Default: CPU count - 1
            use_processes: Use ProcessPoolExecutor instead of ThreadPoolExecutor
        """
        if max_workers is None:
            max_workers = max(1, os.cpu_count() - 1) if os.cpu_count() else 1

        self.max_workers = max_workers
        self.use_processes = use_processes
        self._executor: Optional[ThreadPoolExecutor] = None
        self._progress_lock = asyncio.Lock()
        self._processed_rows = 0
        self._total_rows = 0

    async def __aenter__(self):
        """Enter async context manager"""
        if self.use_processes:
            self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        else:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    async def process_batches_parallel(
        self,
        batches: List[List[Dict[str, Any]]],
        process_func: Callable[[List[Dict[str, Any]]], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Any]:
        """
        Process multiple batches in parallel.

        Args:
            batches: List of batch data (each batch is a list of row dicts)
            process_func: Function to process each batch
            progress_callback: Optional callback(processed_rows, total_rows)

        Returns:
            List of results from each batch
        """
        if not self._executor:
            raise RuntimeError("ParallelBatchProcessor must be used as async context manager")

        self._total_rows = sum(len(batch) for batch in batches)
        self._processed_rows = 0

        loop = asyncio.get_event_loop()

        async def process_with_progress(batch: List[Dict[str, Any]]) -> Any:
            # Run in thread pool
            result = await loop.run_in_executor(self._executor, process_func, batch)

            # Update progress
            async with self._progress_lock:
                self._processed_rows += len(batch)
                if progress_callback:
                    progress_callback(self._processed_rows, self._total_rows)

            return result

        # Create tasks for all batches
        tasks = [process_with_progress(batch) for batch in batches]

        # Process in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    @property
    def worker_count(self) -> int:
        """Get the number of workers"""
        return self.max_workers


class MemoryTracker:
    """
    Tracks memory usage during import.
    """

    def __init__(self):
        self._initial_memory = 0
        self._peak_memory = 0
        self._current_memory = 0

    def start_tracking(self) -> None:
        """Start memory tracking"""
        try:
            process = psutil.Process()
            self._initial_memory = process.memory_info().rss
            self._peak_memory = self._initial_memory
        except Exception:
            pass

    def update(self) -> None:
        """Update memory tracking"""
        try:
            process = psutil.Process()
            self._current_memory = process.memory_info().rss
            self._peak_memory = max(self._peak_memory, self._current_memory)
        except Exception:
            pass

    @property
    def initial_memory_mb(self) -> float:
        """Get initial memory in MB"""
        return self._initial_memory / (1024 * 1024)

    @property
    def peak_memory_mb(self) -> float:
        """Get peak memory in MB"""
        return self._peak_memory / (1024 * 1024)

    @property
    def current_memory_mb(self) -> float:
        """Get current memory in MB"""
        return self._current_memory / (1024 * 1024)


class StreamingCSVReader:
    """
    Streaming CSV reader for large files.

    Reads CSV file in chunks without loading entire file into memory.
    """

    def __init__(
        self,
        file_path: str,
        chunk_size: int = 10000,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ):
        """
        Initialize streaming CSV reader.

        Args:
            file_path: Path to CSV file
            chunk_size: Number of rows per chunk
            encoding: File encoding
            delimiter: CSV delimiter
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.encoding = encoding
        self.delimiter = delimiter

    async def read_chunks(self):
        """
        Async generator that yields chunks of data.

        Yields:
            pandas DataFrame chunks
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for streaming CSV reading")

        # Use pandas chunked reading
        for chunk in pd.read_csv(
            self.file_path,
            chunksize=self.chunk_size,
            encoding=self.encoding,
            delimiter=self.delimiter,
        ):
            yield chunk
            # Allow other async tasks to run
            await asyncio.sleep(0)

    def count_rows(self) -> int:
        """
        Count total rows in file (for progress tracking).

        Returns:
            Total row count (excluding header)
        """
        count = 0
        with open(self.file_path, 'r', encoding=self.encoding) as f:
            # Skip header
            next(f, None)
            for _ in f:
                count += 1
        return count

