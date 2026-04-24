# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
import yaml
import os
from typing import cast


def get_prompt(mode: str, service: str) -> str:
    """
    Load the prompt for the specified service from services/{mode}/prompts.yaml.
    """
    path = f"app/services/{mode}/prompts.yaml"
    if not os.path.exists(path):
        return "[Default prompt]"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return cast(str, data.get(service, "[No specific prompt found]"))
