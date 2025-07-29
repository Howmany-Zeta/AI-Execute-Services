AI_SERVICE_REGISTRY = {}

def register_ai_service(mode: str, service: str):
    """
    装饰器用于将某个类注册到服务中心中，以便通过 (mode, service) 查找调用。
    """
    def decorator(cls):
        AI_SERVICE_REGISTRY[(mode, service)] = cls
        return cls
    return decorator

def get_ai_service(mode: str, service: str):
    """
    根据 mode 和 service 名称查找注册的服务类。
    """
    key = (mode, service)
    if key not in AI_SERVICE_REGISTRY:
        raise ValueError(f"No registered service for mode '{mode}', service '{service}'")
    return AI_SERVICE_REGISTRY[key]
