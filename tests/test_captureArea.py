"""Regression tests for the capture rectangle without a running NVDA session."""

import importlib.util
import sys
import unittest
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


RectLTWH = namedtuple("RectLTWH", "left top width height")
source = Path(__file__).resolve().parents[1] / "addon/globalPlugins/screenshot/rectangleHandler.py"
spec = importlib.util.spec_from_file_location("rectangleHandler", source)
handler = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
	"api": Mock(),
	"locationHelper": SimpleNamespace(RectLTWH=RectLTWH),
	"logHandler": SimpleNamespace(log=Mock()),
	"screenBitmap": Mock(),
	"wx": Mock(),
}):
	spec.loader.exec_module(handler)


class CaptureAreaTests(unittest.TestCase):
	def test_outline_follows_reference_object(self):
		outline = Mock()
		obj = SimpleNamespace(location=RectLTWH(120, 45, 80, 60), container=None)
		rectangle = handler.Rectangle(outline=outline).fromObject(obj)
		outline.showFor.assert_called_once_with(obj.location)
		obj.location = RectLTWH(170, 60, 55, 40)
		rectangle.adjustToObject()
		outline.showFor.assert_called_with(obj.location)

	def test_outline_is_hidden_while_reading_screen_pixels(self):
		visible = True

		@contextmanager
		def hiddenForCapture():
			nonlocal visible
			visible = False
			try:
				yield
			finally:
				visible = True

		obj = SimpleNamespace(location=RectLTWH(120, 45, 80, 60), container=None)
		outline = SimpleNamespace(showFor=Mock(), hiddenForCapture=hiddenForCapture)
		rectangle = handler.Rectangle(outline=outline).fromObject(obj)
		pixels = object()

		def captureImage(*bounds):
			self.assertFalse(visible)
			self.assertEqual(bounds, obj.location)
			return pixels

		backend = Mock()
		backend.ScreenBitmap.return_value.captureImage.side_effect = captureImage
		with patch.multiple(handler, screenBitmap=backend, ctypes=Mock(), Timer=Mock()):
			self.assertIs(rectangle.getRGBQUAD_Array(), pixels)
		self.assertTrue(visible)
