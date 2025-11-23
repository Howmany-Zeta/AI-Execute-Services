"""
Text Chunker

Splits large texts into manageable chunks for processing.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """
    A chunk of text with metadata

    Attributes:
        text: The chunk text content
        start_char: Starting character position in original text
        end_char: Ending character position in original text
        chunk_index: Index of this chunk (0-based)
        metadata: Optional metadata about this chunk
    """

    text: str
    start_char: int
    end_char: int
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """
    Split large texts into smaller chunks

    Strategies:
    - Fixed size chunking (by character or token count)
    - Sentence-aware chunking (don't break sentences)
    - Paragraph-aware chunking (preserve paragraphs)
    - Overlapping chunks (for context preservation)

    Example:
        ```python
        chunker = TextChunker(chunk_size=1000, overlap=100)
        chunks = chunker.chunk_text(long_document)

        for chunk in chunks:
            # Process each chunk separately
            result = await process(chunk.text)
        ```
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 100,
        respect_sentences: bool = True,
        respect_paragraphs: bool = False,
        min_chunk_size: int = 100,
    ):
        """
        Initialize text chunker

        Args:
            chunk_size: Target size for each chunk (in characters)
            overlap: Number of characters to overlap between chunks
            respect_sentences: Try to break at sentence boundaries
            respect_paragraphs: Try to break at paragraph boundaries
            min_chunk_size: Minimum chunk size (don't create tiny chunks)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.respect_sentences = respect_sentences
        self.respect_paragraphs = respect_paragraphs
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """
        Split text into chunks

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of TextChunk objects
        """
        if not text:
            return []

        # Handle short texts
        if len(text) <= self.chunk_size:
            return [
                TextChunk(
                    text=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                    metadata=metadata or {},
                )
            ]

        # Choose chunking strategy
        if self.respect_paragraphs:
            return self._chunk_by_paragraphs(text, metadata)
        elif self.respect_sentences:
            return self._chunk_by_sentences(text, metadata)
        else:
            return self._chunk_fixed_size(text, metadata)

    def _chunk_fixed_size(self, text: str, metadata: Optional[Dict[str, Any]]) -> List[TextChunk]:
        """
        Chunk text by fixed size with overlap

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of TextChunk objects
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            chunk = TextChunk(
                text=text[start:end],
                start_char=start,
                end_char=end,
                chunk_index=chunk_index,
                metadata=metadata or {},
            )
            chunks.append(chunk)

            # Move to next chunk with overlap
            start += self.chunk_size - self.overlap
            chunk_index += 1

        return chunks

    def _chunk_by_sentences(self, text: str, metadata: Optional[Dict[str, Any]]) -> List[TextChunk]:
        """
        Chunk text respecting sentence boundaries

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of TextChunk objects
        """
        # Simple sentence splitting (can be improved with NLTK/spaCy)
        sentences = self._split_sentences(text)

        chunks: List[TextChunk] = []
        current_chunk: List[str] = []
        current_length = 0
        current_start = 0
        chunk_index = 0

        for sent in sentences:
            sent_length = len(sent)

            # If adding this sentence would exceed chunk_size
            if current_length + sent_length > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = " ".join(current_chunk)
                chunk_end = current_start + len(chunk_text)

                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        start_char=current_start,
                        end_char=chunk_end,
                        chunk_index=chunk_index,
                        metadata=metadata or {},
                    )
                )

                # Start new chunk with overlap (last few sentences)
                overlap_sentences: List[str] = self._get_overlap_sentences(current_chunk)
                current_chunk = overlap_sentences
                current_length = sum(len(s) + 1 for s in current_chunk)  # +1 for spaces
                current_start = chunk_end - current_length
                chunk_index += 1

            current_chunk.append(sent)
            current_length += sent_length + 1  # +1 for space

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    start_char=current_start,
                    end_char=len(text),
                    chunk_index=chunk_index,
                    metadata=metadata or {},
                )
            )

        return chunks

    def _chunk_by_paragraphs(self, text: str, metadata: Optional[Dict[str, Any]]) -> List[TextChunk]:
        """
        Chunk text respecting paragraph boundaries

        Args:
            text: Text to chunk
            metadata: Optional metadata

        Returns:
            List of TextChunk objects
        """
        # Split by double newlines (paragraphs)
        paragraphs = text.split("\n\n")

        chunks: List[TextChunk] = []
        current_chunk: List[str] = []
        current_length = 0
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_length = len(para)

            # If adding this paragraph would exceed chunk_size
            if current_length + para_length > self.chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_chunk)
                chunk_end = current_start + len(chunk_text)

                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        start_char=current_start,
                        end_char=chunk_end,
                        chunk_index=chunk_index,
                        metadata=metadata or {},
                    )
                )

                # Start new chunk
                current_chunk = []
                current_length = 0
                current_start = chunk_end
                chunk_index += 1

            current_chunk.append(para)
            current_length += para_length + 2  # +2 for \n\n

        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    start_char=current_start,
                    end_char=len(text),
                    chunk_index=chunk_index,
                    metadata=metadata or {},
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences (simple implementation)

        For production, consider using NLTK's sent_tokenize or spaCy.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        import re

        # Simple sentence splitting by period, question mark, exclamation
        # This is a basic implementation - can be improved
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """
        Get last few sentences for overlap

        Args:
            sentences: List of sentences

        Returns:
            Last few sentences that fit in overlap size
        """
        if not sentences or self.overlap == 0:
            return []

        overlap_sentences: List[str] = []
        overlap_length = 0

        # Take sentences from end until we reach overlap size
        for sent in reversed(sentences):
            if overlap_length + len(sent) + 1 <= self.overlap:
                overlap_sentences.insert(0, sent)
                overlap_length += len(sent) + 1
            else:
                break

        return overlap_sentences
