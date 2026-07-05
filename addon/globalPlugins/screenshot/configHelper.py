#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Configuration helpers for the screenshots wizard NVDA add-on.

The settings panel and the wizard scripts read their settings directly from
config.conf.profiles[0]["screenshots"] (the base/normal profile) so that the
screenshots configuration is global rather than per-profile.

Unlike the merged view config.conf["screenshots"], that raw profile section does
NOT apply the confspec defaults: it only contains the keys that were physically
written to nvda.ini. Therefore every setting has to be materialized explicitly,
otherwise upgrading from a version that stored fewer keys leaves the section
incomplete and reading a missing key (for example "format") raises KeyError as
soon as the settings panel is opened.

This module deliberately avoids importing anything from NVDA so that the
migration logic can be unit tested in isolation.
"""

import os


def ensureBaseProfileConfig(conf, confspec):
	"""Make sure the base (normal) profile holds every screenshots setting.

	Any key missing from config.conf.profiles[0]["screenshots"] is backfilled
	from the validated/merged configuration (config.conf["screenshots"]), which
	does apply the confspec defaults. On first use the folder default is "/",
	in which case it is pointed at the user's documents folder.

	@param conf: the NVDA configuration manager (config.conf) or a compatible
		mapping exposing profiles[0] and __getitem__.
	@param confspec: the mapping of setting names to configspec strings.
	@return: the base profile "screenshots" section, with all keys present.
	"""
	baseProfile = conf.profiles[0]
	if "screenshots" not in baseProfile:
		baseProfile["screenshots"] = {}
	section = baseProfile["screenshots"]
	for key in confspec:
		if key not in section:
			# The merged view applies the confspec defaults for missing keys.
			section[key] = conf["screenshots"][key]
	# On first use there is no folder assigned yet (the spec default is "/").
	# The user's documents folder is assumed as the place to save the images.
	if section["folder"] == "/":
		section["folder"] = os.path.join(os.getenv("USERPROFILE"), "documents")
	return section
