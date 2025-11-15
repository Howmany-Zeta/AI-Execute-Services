import yaml
import os


def get_prompt(mode: str, service: str) -> str:
    """
    Load the prompt for the specified service from services/{mode}/prompts.yaml.
    """
    path = f"app/services/{mode}/prompts.yaml"
    if not os.path.exists(path):
        return "[Default prompt]"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get(service, "[No specific prompt found]")
