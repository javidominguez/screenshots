#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Screenshots Wizard unistall tasks

This file is covered by the GNU General Public License.
Copyright (C) Javi Dominguez 2022
"""

def onUninstall():
	import config
	if "screenshots" in config.conf.spec: del(config.conf.spec["screenshots"])
	if "screenshots" in config.conf.profiles[0]: del(config.conf.profiles[0]["screenshots"])
	