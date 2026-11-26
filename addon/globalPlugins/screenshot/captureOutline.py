# This file is covered by the GNU General Public License.

from contextlib import contextmanager
from ctypes import windll
from ctypes.wintypes import HANDLE, HWND

import winUser
import wx


class _PreviewWindow(wx.Frame):
	"""A click-through, topmost window that never takes keyboard focus."""

	def __init__(self, opacity=100):
		super().__init__(None, style=wx.BORDER_NONE | wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP)
		self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
		self._colorKey = wx.Colour(255, 0, 255)
		self.SetBackgroundColour(self._colorKey)
		hwnd = self.GetHandle()
		style = winUser.getExtendedWindowStyle(hwnd)
		style |= winUser.WS_EX_LAYERED | winUser.WS_EX_TRANSPARENT | winUser.WS_EX_NOACTIVATE
		winUser.setExtendedWindowStyle(hwnd, style)
		winUser.SetLayeredWindowAttributes(
			hwnd, self._colorKey.GetRGB(), round(opacity * 255 / 100), winUser.LWA_COLORKEY | winUser.LWA_ALPHA,
		)
		# Keep a screen-sized preview out of the shell's full-screen app detection.
		windll.user32.SetPropW(HWND(hwnd), "NonRudeHWND", HANDLE(1))

	def Destroy(self):
		windll.user32.RemovePropW(HWND(self.GetHandle()), "NonRudeHWND")
		return super().Destroy()

	def _showOnTop(self):
		if not self.IsShown():
			self.ShowWithoutActivating()
		# The taskbar is topmost too. Keep the preview above it without taking focus.
		windll.user32.SetWindowPos(
			HWND(self.GetHandle()), winUser.HWND_TOPMOST, 0, 0, 0, 0,
			winUser.SWP_NOACTIVATE | winUser.SWP_NOMOVE | winUser.SWP_NOSIZE,
		)


class _DesktopShade(_PreviewWindow):
	"""A translucent black background with a transparent opening for the selection."""

	def __init__(self, opacity):
		super().__init__(opacity)
		self._selection = wx.Rect()
		self.Bind(wx.EVT_PAINT, self._onPaint)

	def setSelection(self, rect):
		previous = self._selection
		self._selection = rect
		if not self.IsShown():
			self.Refresh(False)
			return
		# Only pixels entering or leaving the selection need a different shade.
		changed = wx.Region(previous)
		changed.Xor(rect)
		for part in changed:
			self.RefreshRect(part, eraseBackground=False)

	def _onPaint(self, event):
		dc = wx.PaintDC(self)
		dc.SetBackground(wx.BLACK_BRUSH)
		dc.Clear()
		dc.SetPen(wx.TRANSPARENT_PEN)
		dc.SetBrush(wx.Brush(self._colorKey))
		dc.DrawRectangle(self._selection)


class CaptureOutline(_PreviewWindow):
	"""A click-through preview in the same screen coordinates as the capture."""

	def __init__(self, dimmingOpacity=0):
		super().__init__()
		self._shade = _DesktopShade(dimmingOpacity) if dimmingOpacity else None
		self._location = None
		self._bands = []
		self._fitDesktop()
		self.Bind(wx.EVT_DISPLAY_CHANGED, self._onDisplayChanged)
		self.Bind(wx.EVT_PAINT, self._onPaint)

	def Hide(self):
		if self._shade is not None:
			self._shade.Hide()
		return super().Hide()

	def Destroy(self):
		if self._shade is not None:
			self._shade.Destroy()
		return super().Destroy()

	def _showOnTop(self):
		if self._shade is not None:
			self._shade._showOnTop()
		super()._showOnTop()

	def _fitDesktop(self):
		bounds = wx.Display(0).GetGeometry()
		for index in range(1, wx.Display.GetCount()):
			bounds = bounds.Union(wx.Display(index).GetGeometry())
		self._origin = bounds.GetTopLeft()
		self.SetSize(*bounds, wx.SIZE_ALLOW_MINUS_ONE)
		if self._shade is not None:
			self._shade.SetSize(*bounds, wx.SIZE_ALLOW_MINUS_ONE)
			self._shade.Refresh(False)

	def _onDisplayChanged(self, event):
		self._fitDesktop()
		if self._location is not None:
			self._updateSelection(self._location)
		self.Refresh(False)
		event.Skip()

	def _updateSelection(self, location):
		self._location = location
		rect = wx.Rect(*location)
		rect.Offset(-self._origin.x, -self._origin.y)
		self._bands = list(self._borderBands(rect))
		if self._shade is not None and self._bands:
			self._shade.setSelection(rect)

	def _borderBands(self, rect):
		left, top, width, height = rect
		stroke = self.FromDIP(2)
		for color in (wx.YELLOW, wx.BLACK):
			if width <= 0 or height <= 0:
				return
			if min(width, height) <= 2 * stroke:
				yield wx.Rect(left, top, width, height), color
				return
			yield wx.Rect(left, top, width, stroke), color
			yield wx.Rect(left, top + height - stroke, width, stroke), color
			yield wx.Rect(left, top + stroke, stroke, height - 2 * stroke), color
			yield wx.Rect(left + width - stroke, top + stroke, stroke, height - 2 * stroke), color
			left += stroke
			top += stroke
			width -= 2 * stroke
			height -= 2 * stroke

	def showFor(self, location):
		location = tuple(location)
		if self._location == location and self.IsShown():
			return
		previous = self._bands
		self._updateSelection(location)
		if not self._bands:
			self.Hide()
			return
		if not self.IsShown():
			self._showOnTop()
		# Let wx coalesce repeated key presses into a paint of the latest border.
		for band, _ in previous + self._bands:
			self.RefreshRect(band, eraseBackground=False)

	def _onPaint(self, event):
		# PaintDC clips to the invalid region, including any part of the old border.
		dc = wx.PaintDC(self)
		dc.SetBackground(wx.Brush(self._colorKey))
		dc.Clear()
		dc.SetPen(wx.TRANSPARENT_PEN)
		for band, color in self._bands:
			dc.SetBrush(wx.Brush(color))
			dc.DrawRectangle(band)

	@contextmanager
	def hiddenForCapture(self):
		if not self.IsShown():
			yield
			return
		self.Hide()
		try:
			# Wait until the compositor has removed the preview before reading pixels.
			windll.dwmapi.DwmFlush()
			yield
		finally:
			self._showOnTop()
