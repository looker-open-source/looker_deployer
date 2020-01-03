import configparser


def read_ini(ini="../looker.ini"):
    config = configparser.ConfigParser()
    config.read(ini)

    return config
