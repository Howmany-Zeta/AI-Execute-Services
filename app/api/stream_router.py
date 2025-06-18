from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.api.service_dispatcher import ServiceDispatcher
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/{mode}/{service}")
async def stream_response(mode: str, service: str, request: Request):
    try:
        data = await request.json()
        service_instance, context = await ServiceDispatcher.dispatch_service(mode, service, data)

        async def event_stream():
            try:
                async for chunk in service_instance.stream(data, context):
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                logger.error(f"Error during streaming for {mode}/{service}: {str(e)}")
                yield f"data: {{ \"status\": \"error\", \"message\": \"服务执行失败，请稍后重试。错误: {str(e)}\" }}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Failed to dispatch service {mode}/{service}: {str(e)}")
        error_message = str(e)  # Capture the error message in a local variable
        async def error_stream():
            yield f"data: {{ \"status\": \"error\", \"message\": \"无法初始化服务，请稍后重试。错误: {error_message}\" }}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")
