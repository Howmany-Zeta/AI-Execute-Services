"""
Document Graph Builder

Builds knowledge graphs from documents (PDF, DOCX, TXT, etc.).
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field

from aiecs.application.knowledge_graph.builder.graph_builder import (
    GraphBuilder,
    BuildResult,
)
from aiecs.application.knowledge_graph.builder.text_chunker import TextChunker
from aiecs.tools.docs.document_parser_tool import (
    DocumentParserTool,
    ParsingStrategy,
    OutputFormat,
)


@dataclass
class DocumentBuildResult:
    """
    Result of document-to-graph build operation

    Extends BuildResult with document-specific information.
    """

    document_path: str
    document_type: str
    total_chunks: int = 0
    chunks_processed: int = 0
    chunk_results: List[BuildResult] = field(default_factory=list)
    success: bool = True
    errors: List[str] = field(default_factory=list)

    @property
    def total_entities_added(self) -> int:
        """Total entities added across all chunks"""
        return sum(r.entities_added for r in self.chunk_results)

    @property
    def total_relations_added(self) -> int:
        """Total relations added across all chunks"""
        return sum(r.relations_added for r in self.chunk_results)


class DocumentGraphBuilder:
    """
    Build knowledge graphs from documents

    Supports multiple document formats:
    - PDF
    - DOCX (Microsoft Word)
    - TXT (Plain text)
    - And more via AIECS DocumentParserTool

    For large documents, automatically chunks text into manageable pieces.

    Example:
        ```python
        builder = DocumentGraphBuilder(
            graph_builder=graph_builder,
            chunk_size=1000
        )

        result = await builder.build_from_document("research_paper.pdf")

        print(f"Processed {result.total_chunks} chunks")
        print(f"Added {result.total_entities_added} entities")
        print(f"Added {result.total_relations_added} relations")
        ```
    """

    def __init__(
        self,
        graph_builder: GraphBuilder,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        enable_chunking: bool = True,
        parallel_chunks: bool = True,
        max_parallel_chunks: int = 3,
    ):
        """
        Initialize document graph builder

        Args:
            graph_builder: GraphBuilder instance for text processing
            chunk_size: Size of text chunks (in characters)
            chunk_overlap: Overlap between chunks
            enable_chunking: Whether to chunk large documents
            parallel_chunks: Process chunks in parallel
            max_parallel_chunks: Maximum parallel chunk processing
        """
        self.graph_builder = graph_builder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_chunking = enable_chunking
        self.parallel_chunks = parallel_chunks
        self.max_parallel_chunks = max_parallel_chunks

        # Initialize document parser (will read config from environment
        # variables)
        self.document_parser = DocumentParserTool()

        # Initialize text chunker
        self.text_chunker = TextChunker(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            respect_sentences=True,
        )

    async def build_from_document(
        self,
        document_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentBuildResult:
        """
        Build knowledge graph from a document

        Args:
            document_path: Path to document file
            metadata: Optional metadata to attach to extracted entities/relations

        Returns:
            DocumentBuildResult with statistics
        """
        document_path = str(document_path)
        result = DocumentBuildResult(document_path=document_path, document_type="unknown")

        try:
            # Step 1: Parse document to text
            text = await self._parse_document(document_path)

            if not text or not text.strip():
                result.success = False
                result.errors.append("Document parsing returned empty text")
                return result

            # Determine document type
            result.document_type = Path(document_path).suffix[1:].lower()  # Remove leading dot

            # Step 2: Chunk text if needed
            if self.enable_chunking and len(text) > self.chunk_size:
                chunks = self.text_chunker.chunk_text(text, metadata={"document": document_path})
                result.total_chunks = len(chunks)
            else:
                # Single chunk (small document)
                from aiecs.application.knowledge_graph.builder.text_chunker import (
                    TextChunk,
                )

                chunks = [
                    TextChunk(
                        text=text,
                        start_char=0,
                        end_char=len(text),
                        chunk_index=0,
                        metadata={"document": document_path},
                    )
                ]
                result.total_chunks = 1

            # Step 3: Process each chunk
            if self.parallel_chunks and len(chunks) > 1:
                # Process chunks in parallel
                chunk_results = await self._process_chunks_parallel(chunks, document_path, metadata)
            else:
                # Process chunks sequentially
                chunk_results = await self._process_chunks_sequential(chunks, document_path, metadata)

            result.chunk_results = chunk_results
            result.chunks_processed = len(chunk_results)

            # Check if all chunks succeeded
            failed_chunks = [r for r in chunk_results if not r.success]
            if failed_chunks:
                result.errors.append(f"{len(failed_chunks)} chunks failed processing")

            result.success = len(failed_chunks) < len(chunks)  # At least some chunks succeeded

        except Exception as e:
            result.success = False
            result.errors.append(f"Document processing failed: {str(e)}")

        return result

    async def build_from_documents(
        self,
        document_paths: List[Union[str, Path]],
        parallel: bool = True,
        max_parallel: int = 3,
    ) -> List[DocumentBuildResult]:
        """
        Build knowledge graph from multiple documents

        Args:
            document_paths: List of document paths
            parallel: Process documents in parallel
            max_parallel: Maximum parallel documents

        Returns:
            List of DocumentBuildResult objects
        """
        if parallel:
            semaphore = asyncio.Semaphore(max_parallel)

            async def process_one(doc_path):
                async with semaphore:
                    return await self.build_from_document(doc_path)

            tasks = [process_one(doc_path) for doc_path in document_paths]
            gather_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions - convert all to DocumentBuildResult
            results: List[DocumentBuildResult] = []
            for i, result in enumerate(gather_results):
                if isinstance(result, Exception):
                    error_result = DocumentBuildResult(
                        document_path=str(document_paths[i]),
                        document_type="unknown",
                        success=False,
                    )
                    error_result.errors.append(str(result))
                    results.append(error_result)
                elif isinstance(result, DocumentBuildResult):
                    results.append(result)
                else:
                    # Fallback for unexpected types
                    error_result = DocumentBuildResult(
                        document_path=str(document_paths[i]),
                        document_type="unknown",
                        success=False,
                    )
                    error_result.errors.append(f"Unexpected result type: {type(result)}")
                    results.append(error_result)

            return results
        else:
            # Sequential processing
            results = []
            for doc_path in document_paths:
                result = await self.build_from_document(doc_path)
                results.append(result)
            return results

    async def _parse_document(self, document_path: str) -> str:
        """
        Parse document to text using AIECS document parser

        Args:
            document_path: Path to document

        Returns:
            Extracted text content
        """
        try:
            # Use document parser tool
            parse_result = self.document_parser.parse_document(
                source=document_path,
                strategy=ParsingStrategy.TEXT_ONLY,
                output_format=OutputFormat.TEXT,
            )

            if isinstance(parse_result, dict):
                return parse_result.get("content", "")
            elif isinstance(parse_result, str):
                return parse_result
            else:
                return ""

        except Exception:
            # Fallback: try reading as plain text
            try:
                with open(document_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as fallback_error:
                raise RuntimeError(f"Failed to parse document: {str(fallback_error)}")

    async def _process_chunks_parallel(
        self,
        chunks: List,
        document_path: str,
        metadata: Optional[Dict[str, Any]],
    ) -> List[BuildResult]:
        """
        Process chunks in parallel

        Args:
            chunks: List of TextChunk objects
            document_path: Source document path
            metadata: Optional metadata

        Returns:
            List of BuildResult objects
        """
        semaphore = asyncio.Semaphore(self.max_parallel_chunks)

        async def process_chunk(chunk):
            async with semaphore:
                chunk_metadata = {
                    "document": document_path,
                    "chunk_index": chunk.chunk_index,
                    "chunk_start": chunk.start_char,
                    "chunk_end": chunk.end_char,
                }
                if metadata:
                    chunk_metadata.update(metadata)

                source = f"{document_path}#chunk{chunk.chunk_index}"
                return await self.graph_builder.build_from_text(text=chunk.text, source=source, metadata=chunk_metadata)

        tasks = [process_chunk(chunk) for chunk in chunks]
        gather_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions - convert all to BuildResult
        results: List[BuildResult] = []
        for i, result in enumerate(gather_results):
            if isinstance(result, Exception):
                error_result = BuildResult(success=False)
                error_result.errors.append(f"Chunk {i} failed: {str(result)}")
                results.append(error_result)
            elif isinstance(result, BuildResult):
                results.append(result)
            else:
                # Fallback for unexpected types
                error_result = BuildResult(success=False)
                error_result.errors.append(f"Unexpected result type: {type(result)}")
                results.append(error_result)

        return results

    async def _process_chunks_sequential(
        self,
        chunks: List,
        document_path: str,
        metadata: Optional[Dict[str, Any]],
    ) -> List[BuildResult]:
        """
        Process chunks sequentially

        Args:
            chunks: List of TextChunk objects
            document_path: Source document path
            metadata: Optional metadata

        Returns:
            List of BuildResult objects
        """
        results = []

        for chunk in chunks:
            chunk_metadata = {
                "document": document_path,
                "chunk_index": chunk.chunk_index,
                "chunk_start": chunk.start_char,
                "chunk_end": chunk.end_char,
            }
            if metadata:
                chunk_metadata.update(metadata)

            source = f"{document_path}#chunk{chunk.chunk_index}"
            result = await self.graph_builder.build_from_text(text=chunk.text, source=source, metadata=chunk_metadata)
            results.append(result)

        return results
