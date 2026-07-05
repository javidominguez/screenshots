#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Regression tests for screenshot.configHelper.ensureBaseProfileConfig.

These tests reproduce the crash reported when opening the "Screenshots Wizard"
settings panel:

    File ".../globalPlugins/screenshot/gui.py", line 45, in makeSettings
        self.radioBoxFormat.SetSelection(
            fileFormats.index(config.conf.profiles[0]["screenshots"]["format"]))
    KeyError: 'format'

The panel and the wizard scripts read config.conf.profiles[0]["screenshots"]
directly (the base/normal profile). That raw section does NOT apply the add-on's
confspec defaults, so any key that was never written to nvda.ini is absent and
raises KeyError. ensureBaseProfileConfig() backfills every missing key.

configHelper imports nothing from NVDA, so this suite runs under a plain Python
interpreter (python tests/test_configHelper.py) as well as under pytest.
"""

import os
import sys
import unittest

# Import the add-on helper directly, without pulling in NVDA.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ADDON_SRC = os.path.join(_HERE, os.pardir, "addon", "globalPlugins", "screenshot")
sys.path.insert(0, _ADDON_SRC)

import configHelper  # noqa: E402


# Mirror of the confspec declared in globalPlugins/screenshot/__init__.py and the
# values a validated configuration returns for those specs.
CONFSPEC = {
	"folder": "string(default=/)",
	"format": "string(default=BMP)",
	"action": "integer(default=2)",
	"step": "integer(default=5)",
	"scale": "boolean(default=false)",
}
SPEC_DEFAULTS = {
	"folder": "/",
	"format": "BMP",
	"action": 2,
	"step": 5,
	"scale": False,
}


class FakeConf:
	"""Minimal stand-in for NVDA's config.conf.

	It models the two access paths the add-on relies on:

	* conf.profiles[0]["screenshots"][key] -- the RAW base-profile section. It
	  only holds keys physically present in nvda.ini; a missing key raises
	  KeyError (no spec defaults are applied). This is what used to crash.
	* conf["screenshots"][key] -- the MERGED view, which applies the confspec
	  defaults for any key not overridden in the profile.
	"""

	def __init__(self, baseSection):
		# baseSection: dict of keys already stored in the profile, or None to
		# model a config that has no [screenshots] section at all.
		self.profiles = [dict()]
		if baseSection is not None:
			self.profiles[0]["screenshots"] = dict(baseSection)
		# Merged view = spec defaults overlaid with whatever the profile stored.
		merged = dict(SPEC_DEFAULTS)
		if baseSection is not None:
			merged.update(baseSection)
		self._merged = {"screenshots": merged}

	def __getitem__(self, key):
		return self._merged[key]


class EnsureBaseProfileConfigTests(unittest.TestCase):

	def setUp(self):
		# ensureBaseProfileConfig points a first-run folder at %USERPROFILE%.
		# Pin it to a known value so assertions are deterministic and platform
		# independent (USERPROFILE is unset on the Linux CI runners).
		self._savedUserProfile = os.environ.get("USERPROFILE")
		os.environ["USERPROFILE"] = os.path.join("X:", "fake_user")

	def tearDown(self):
		if self._savedUserProfile is None:
			os.environ.pop("USERPROFILE", None)
		else:
			os.environ["USERPROFILE"] = self._savedUserProfile

	def test_reproduces_original_keyerror(self):
		"""A partially-upgraded profile crashes on the raw 'format' read."""
		conf = FakeConf({"folder": r"C:\Users\admin\documents", "scale": False})
		# This is exactly the expression gui.py used at the point of the crash.
		with self.assertRaises(KeyError):
			conf.profiles[0]["screenshots"]["format"]

	def test_partial_upgrade_backfills_missing_keys(self):
		"""Missing keys are filled from the spec defaults; existing ones kept."""
		conf = FakeConf({"folder": r"C:\Users\admin\documents", "scale": False})
		section = configHelper.ensureBaseProfileConfig(conf, CONFSPEC)
		# Every declared setting is now present in the raw profile section.
		for key in CONFSPEC:
			self.assertIn(key, section, "missing key after backfill: %r" % key)
		# Backfilled keys took the spec defaults.
		self.assertEqual(section["format"], "BMP")
		self.assertEqual(section["action"], 2)
		self.assertEqual(section["step"], 5)
		# Pre-existing user values were preserved untouched.
		self.assertEqual(section["folder"], r"C:\Users\admin\documents")
		self.assertEqual(section["scale"], False)
		# The formerly-crashing panel expression now succeeds.
		self.assertEqual(conf.profiles[0]["screenshots"]["format"], "BMP")

	def test_fresh_install_creates_section_and_points_folder(self):
		"""With no [screenshots] section, one is created with all defaults."""
		conf = FakeConf(None)
		section = configHelper.ensureBaseProfileConfig(conf, CONFSPEC)
		self.assertIn("screenshots", conf.profiles[0])
		for key in CONFSPEC:
			self.assertIn(key, section)
		# The "/" folder default is replaced by the user's documents folder.
		self.assertEqual(
			section["folder"],
			os.path.join(os.environ["USERPROFILE"], "documents"),
		)
		self.assertEqual(section["format"], "BMP")

	def test_existing_complete_config_is_untouched(self):
		"""A fully-populated profile is returned verbatim (idempotent)."""
		custom = {
			"folder": r"D:\shots",
			"format": "PNG",
			"action": 1,
			"step": 3,
			"scale": True,
		}
		conf = FakeConf(dict(custom))
		section = configHelper.ensureBaseProfileConfig(conf, CONFSPEC)
		self.assertEqual(section, custom)

	def test_folder_slash_replaced_even_when_section_exists(self):
		"""A leftover '/' folder is resolved to documents on any run."""
		conf = FakeConf({"folder": "/"})
		section = configHelper.ensureBaseProfileConfig(conf, CONFSPEC)
		self.assertEqual(
			section["folder"],
			os.path.join(os.environ["USERPROFILE"], "documents"),
		)

	def test_confspec_and_defaults_stay_in_sync(self):
		"""Guard: the test's default table matches the declared confspec keys."""
		self.assertEqual(set(CONFSPEC), set(SPEC_DEFAULTS))


if __name__ == "__main__":
	unittest.main(verbosity=2)
