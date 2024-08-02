from benedict import benedict


def load_stage_config(stage: str) -> dict:

    config_path = f"config/{stage}.yml"

    config = benedict.from_yaml(config_path)
    config["stage"] = stage

    return config

def normalize_resource_name(name: str) -> str:
    tokens= name.lower().split("-")
    return "".join([token.capitalize() for token in tokens])