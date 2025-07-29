from app.config.registry import register_ai_service
from app.services.base_service import BaseAIService
from asyncio import sleep

@register_ai_service("domain", "summarizer")
class DomainSummarizer(BaseAIService):
    def run(self, input_data, context):
        return {"result": f"[Domain] Summary (regulated): {input_data.get('text', '')}"}

    async def stream(self, input_data, context):
        text = input_data.get("text", "")
        for i, word in enumerate(text.split()):
            await sleep(0.25)
            yield f'{{"role": "assistant", "content": "[Expert] {word} "}}'
