import yaml

CONFIG_PATH = "config.yaml"


def read_config(path):
    with open(path) as fh:
        config = yaml.load(fh.read(), Loader=yaml.FullLoader)
    return config
