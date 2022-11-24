#!/usr/bin/env python3
from __future__ import annotations
# TODO: replace with async?
from pysiaalarm import SIAClient, SIAAccount, SIAEvent
from typing import NamedTuple, Optional
from time import sleep
from os import environ
from paho.mqtt.client import Client as MqttClient
import toml

def handle_event(event: SIAEvent) -> None:
    #print(event)
    print(event.ri, event.code)
    assert event.valid_message
    parsed = ParsedEvent.from_sia(event)
    print(parsed)
    if parsed:
        mqtt.publish(f"sia/{parsed.type_}", parsed.triggered)

class ParsedEvent(NamedTuple):
    type_: int
    triggered: bool

    @classmethod
    def from_sia(cls, event: SIAEvent) -> Optional[ParsedEvent]:
        if not event.ri:
            print(f"unknown event ri")
            return None
        type_ = int(event.ri)
        match event.code:
            case "BA" | "FA" | "YX":
                triggered = True
            case "BH" | "FH" | "YZ":
                triggered = False
            case code:
                print(f"unknown event code: {code}")
                return None
        return cls(type_, triggered)

config = toml.load(environ.get("CONFIG_FILE", "siamqtt.toml"))
sia = SIAClient(
    config["sia"]["bind"],
    config["sia"]["port"],
    [SIAAccount(account) for account in config["sia"]["accounts"]],
    handle_event,
)
mqtt = MqttClient()
mqtt.connect(config["mqtt"]["server"])

with sia as s:
    while True:
        sleep(500)
