#!/usr/bin/env python3
from __future__ import annotations
import atexit
# TODO: replace with async?
from pysiaalarm import SIAClient, SIAAccount, SIAEvent
from typing import NamedTuple, Optional
from time import sleep
from os import environ
import logging
from pathlib import Path
import json
from paho.mqtt.client import Client as MqttClient
import toml

DSN_PATH = Path("/run/secrets/SIAMQTT_SENTRY_DSN")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def handle_event(event: SIAEvent) -> None:
    logger.debug("got ri %s and code %s", event.ri, event.code)
    assert event.valid_message
    parsed = ParsedEvent.from_sia(event)
    logger.debug("parsed: %s", parsed)
    parsed.publish_to_mqtt()

def hass_topic_for_zone(zone: int) -> str:
    return f"homeassistant/binary_sensor/sia-{zone}/state"

class ParsedEvent(NamedTuple):
    zone: int
    triggered: bool

    @classmethod
    def from_sia(cls, event: SIAEvent) -> ParsedEvent:
        if not event.ri:
            raise ValueError("unknown event ri")
        zone = int(event.ri)
        match event.code:
            case "BA" | "FA" | "YX":
                triggered = True
            case "BH" | "FH" | "YZ":
                triggered = False
            case code:
                raise NotImplementedError(f"unknown event code: {code}")
        return cls(zone, triggered)
    
    def publish_to_mqtt(self) -> None:
        if "homeassistant" in config["mqtt"]:
            mqtt.publish(
                hass_topic_for_zone(self.zone),
                "ON" if self.triggered else "OFF",
                retain=True,
            )
        else:
            mqtt.publish(
                f"sia/{self.zone}",
                str(self.triggered).lower(),
                retain=True,
                )
                

if DSN_PATH.exists():
    logger.info("Configuring Sentry...")
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    sentry_logging = LoggingIntegration(
        level=logging.INFO, # Capture as breadcrumbs
        event_level=logging.WARNING, # Send as events
    )
    sentry_sdk.init(DSN_PATH.read_text().strip())

config = toml.load(environ.get("CONFIG_FILE", "siamqtt.toml"))
sia = SIAClient(
    config["sia"]["bind"],
    config["sia"]["port"],
    [SIAAccount(account) for account in config["sia"]["accounts"]],
    handle_event,
)
mqtt = MqttClient()
mqtt.connect(config["mqtt"]["server"])

if "homeassistant" in config["mqtt"]:
    logger.info("Registering devices with hass...")
    for zone, zone_conf in config["mqtt"]["homeassistant"]["device"].items():
        mqtt.publish(
            f"homeassistant/binary_sensor/sia-{zone}/config",
            json.dumps({
                "name": zone_conf["name"],
                "state_topic": hass_topic_for_zone(zone),
            }),
            retain=True,
        )


def on_exit() -> None:
    if "homeassistant" in config["mqtt"]:
        logger.info("Deregistering from hass...")
        for zone in config["mqtt"]["homeassistant"]["device"]:
            mqtt.publish(
                f"homeassistant/binary_sensor/sia-{zone}/config",
                "",
                retain=True,
            )

atexit.register(on_exit)

with sia as s:
    logger.info("Waiting for events...")
    while True:
        sleep(500)
