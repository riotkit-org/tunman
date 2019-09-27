# -*- coding: utf-8 -*-
"""Application configuration."""
import os


class Config(object):
    """Base configuration."""

    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    CONFIG_PATH = os.getenv('CONFIG_PATH', os.path.abspath(os.path.dirname(__file__)))
    LOG_LEVEL = 'info'
    LOG_PATH = './tunman.log'
    SECRET_PREFIX = ''


class ProdConfig(Config):
    """Production configuration."""

    ENV = 'prod'
    DEBUG = False


class DevConfig(Config):
    """Development configuration."""

    ENV = 'dev'
    DEBUG = True
    LOG_LEVEL = 'debug'

