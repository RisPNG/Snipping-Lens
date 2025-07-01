import os


class DevelopmentConfig:

    SECRET_KEY = os.urandom(24)
    DEBUG = True
    TESTING = False


class TestingConfig:

    SECRET_KEY = os.urandom(24)
    DEBUG = True
    TESTING = True


class ProductionConfig:

    SECRET_KEY = os.urandom(24)
    DEBUG = False
    TESTING = False


config_by_name = dict(dev=DevelopmentConfig, test=TestingConfig, prod=ProductionConfig)

