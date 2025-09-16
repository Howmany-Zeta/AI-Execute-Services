AI_SERVICE_REGISTRY = {}

def register_ai_service(mode: str, service: str):
    """
    Decorator for registering a class to the service center, so it can be found and called by (mode, service).
    """
    def decorator(cls):
        AI_SERVICE_REGISTRY[(mode, service)] = cls
        return cls
    return decorator

def get_ai_service(mode: str, service: str):
    """
    Find registered service class based on mode and service name.
    """
    key = (mode, service)
    if key not in AI_SERVICE_REGISTRY:
        raise ValueError(f"No registered service for mode '{mode}', service '{service}'")
    return AI_SERVICE_REGISTRY[key]
