# disneyworld-reservation-but-not-shit

![license](https://img.shields.io/github/license/ipwnponies/disneyworld-reservation-but-not-shit.svg)

## Dependencies

This script uses `Selenium` to load websites, webdrivers will need to be installed.
In particular, this was written and tested on a `Firefox` headless driver.

## How to Use

Install `virtualenv`:

```sh
make venv-deploy
```

Configure:

```sh
cp config.yaml.template ~/.config/disney-reservation/config.yaml
# Edit config values
```

Run:

```sh
venv/bin/python -m disney_reservation
```
