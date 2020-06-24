import looker_sdk


def get_client(ini, env):
    sdk = looker_sdk.init31(config_file=ini, section=env)
    return sdk
