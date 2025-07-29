from app.config.registry import register_ai_service
from app.services.base_service import BaseAIService
from app.services.scholar.services.rag import build_graph
from app.services.scholar.services.rag.vector_store_factory import VectorStoreFactory

@register_ai_service("scholar", "rag")
class DomainRAGService(BaseAIService):
    """
    Domain-specific RAG service that provides knowledge graph functionality
    Now using Vertex AI Vector Search instead of Qdrant
    """
    def __init__(self):
        super().__init__()
        self.vector_store = VectorStoreFactory.create_vector_store()

    def run(self, input_data, context):
        """
        Generate knowledge graph for a document or retrieve context for a query

        Expected input_data format for graph generation:
        {
            "doc_id": "document_id",
            "threshold": 0.5  # optional
        }

        Expected input_data format for query:
        {
            "query": "user query text"
        }
        """
        # Handle graph generation
        if "doc_id" in input_data:
            doc_id = input_data.get("doc_id")
            threshold = input_data.get("threshold", 0.5)

            if not doc_id:
                return {"error": "Missing document ID"}

            try:
                vectors = self.vector_store.get_vectors(doc_id)
                graph = build_graph(vectors, threshold=threshold)
                return {"graph": graph}
            except Exception as e:
                return {"error": str(e)}

        # Handle text query
        elif "query" in input_data:
            query = input_data.get("query")
            # Implement RAG retrieval logic here
            # This is a placeholder that mimics the behavior of the original RAG tool
            return {"result": f"[RAG retrieved]: context for '{query}'"}

        else:
            return {"error": "Invalid input: requires either 'doc_id' or 'query'"}

    async def stream(self, input_data, context):
        """
        OpenAI兼容的流式响应方法
        """
        # 创建OpenAI兼容的流式格式化器
        formatter = self.create_stream_formatter("domain-rag")

        try:
            result = self.run(input_data, context)

            # For error cases
            if "error" in result:
                yield self.format_stream_error(formatter, result["error"], "service_error")
                yield self.format_stream_done(formatter)
                return

            # For graph generation
            if "graph" in result:
                yield self.format_stream_chunk(formatter, "Generating knowledge graph...")
                import asyncio
                await asyncio.sleep(0.1)  # Simulate processing time
                yield self.format_stream_chunk(formatter, f"Graph generated: {str(result['graph'])}")
                yield self.format_stream_chunk(formatter, "", finish_reason="stop")
                yield self.format_stream_done(formatter)

            # For text query
            elif "result" in result:
                # Simulate streaming for text responses
                words = result["result"].split()
                for i, word in enumerate(words):
                    if i % 3 == 0 and i > 0:  # Group words for smoother streaming
                        chunk = " ".join(words[i-3:i]) + " "
                        yield self.format_stream_chunk(formatter, chunk)
                        import asyncio
                        await asyncio.sleep(0.05)

                # Yield any remaining words
                remaining = len(words) % 3
                if remaining > 0:
                    chunk = " ".join(words[-remaining:])
                    yield self.format_stream_chunk(formatter, chunk)

                yield self.format_stream_chunk(formatter, "", finish_reason="stop")
                yield self.format_stream_done(formatter)

        except Exception as e:
            yield self.format_stream_error(formatter, f"An error occurred: {str(e)}", "service_error")
            yield self.format_stream_done(formatter)
