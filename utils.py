from benedict import benedict


def load_stage_config(stage: str) -> dict:

    config_path = f"config/{stage}.yml"

    return benedict.from_yaml(config_path)
