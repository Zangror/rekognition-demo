#!/usr/bin/env python3
import monocdk as core

from infrastructure.main import DemoStack

environment = core.Environment(region="eu-west-1", account="993176408040")

app = core.App()

DemoStack(app, "DemoStack")

app.synth()
