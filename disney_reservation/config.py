import sys
from functools import lru_cache
from pathlib import Path
from typing import List

import attr
from strictyaml import Bool
from strictyaml import load
from strictyaml import Map
from strictyaml import Seq
from strictyaml import Str
from strictyaml import UniqueSeq
from xdg import XDG_CONFIG_HOME

CONFIG_DIR = Path(XDG_CONFIG_HOME) / 'disney-reservation'


@attr.s
class Restaurant:
    url: str
    name: str


@attr.s
class Mail:
    enable: bool
    sender: str
    password: str
    smtp_server: str
    recipients: List[str] = attr.ib(factory=list)


@attr.s
class Config:
    restaurants: List[Restaurant] = attr.ib(factory=list)
    mail: Mail = attr.ib()


@lru_cache(maxsize=1)
def config() -> Config:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config_file = CONFIG_DIR / 'config.yaml'
    if not config_file.exists():
        sys.exit(f'{config_file} not found')

    restaurant_schema = Map({
        'url': Str(),
        'name': Str(),
    })
    schema = Map({
        'restaurants': Seq(restaurant_schema),
        'mail': Map({
            'enable': Bool(),
            'sender': Str(),
            'password': Str(),
            'smtp_server': Str(),
            'recipients': UniqueSeq(Str()),
        }),
    })

    yaml = load(config_file.read_text(), schema)
    _config = Config()

    for i in yaml.get('restaurants', []):
        restaurant = Restaurant(i['url'], i['name'])
        _config.restaurants.append(restaurant)

    mail_config = Mail(
        enable=yaml['mail']['enable'],
        sender=yaml['mail']['sender'],
        password=yaml['mail']['password'],
        smtp_server=yaml['mail']['smtp_server'],
        recipients=yaml['mail']['recipients'],
    )
    _config.mail = mail_config

    return _config
