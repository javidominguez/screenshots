# This file is covered by the GNU General Public License.

from contextlib import contextmanager
from ctypes import windll
from ctypes.wintypes import HANDLE, HWND

import winUser
import wx


class CaptureOutline(wx.Frame):
	"""A click-through preview in the same screen coordinates as the capture."""

	def __init__(self):
		super().__init__(None, style=wx.BORDER_NONE | wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP)
		self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
		self._colorKey = wx.Colour(255, 0, 255)
		self.SetBackgroundColour(self._colorKey)
		hwnd = self.GetHandle()
		style = winUser.getExtendedWindowStyle(hwnd)
		style |= winUser.WS_EX_LAYERED | winUser.WS_EX_TRANSPARENT | winUser.WS_EX_NOACTIVATE
		winUser.setExtendedWindowStyle(hwnd, style)
		winUser.SetLayeredWindowAttributes(hwnd, self._colorKey.GetRGB(), 0, winUser.LWA_COLORKEY)
		# Keep a screen-sized preview out of the shell's full-screen app detection.
		windll.user32.SetPropW(HWND(hwnd), "NonRudeHWND", HANDLE(1))
		self._location = None
		self._bands = []
		self._fitDesktop()
		self.Bind(wx.EVT_DISPLAY_CHANGED, self._onDisplayChanged)
		self.Bind(wx.EVT_PAINT, self._onPaint)

	def Destroy(self):
		windll.user32.RemovePropW(HWND(self.GetHandle()), "NonRudeHWND")
		return super().Destroy()

	def _fitDesktop(self):
		bounds = wx.Display(0).GetGeometry()
		for index in range(1, wx.Display.GetCount()):
			bounds = bounds.Union(wx.Display(index).GetGeometry())
		self._origin = bounds.GetTopLeft()
		self.SetSize(*bounds, wx.SIZE_ALLOW_MINUS_ONE)

	def _onDisplayChanged(self, event):
		self._fitDesktop()
		if self._location is not None:
			self._bands = list(self._borderBands(self._location))
		self.Refresh(False)
		event.Skip()

	def _borderBands(self, location):
		left, top, width, height = location
		left -= self._origin.x
		top -= self._origin.y
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
		previous = self._bands
		self._location = location
		self._bands = list(self._borderBands(location))
		if not self._bands:
			self.Hide()
			return
		if not self.IsShown():
			self._showOnTop()
		# Let wx coalesce repeated key presses into a paint of the latest border.
		for band, _ in previous + self._bands:
			self.RefreshRect(band, eraseBackground=False)

	def _showOnTop(self):
		if not self.IsShown():
			self.ShowWithoutActivating()
		# The taskbar is topmost too. Keep the outline above it without taking focus.
		windll.user32.SetWindowPos(
			HWND(self.GetHandle()), winUser.HWND_TOPMOST, 0, 0, 0, 0,
			winUser.SWP_NOACTIVATE | winUser.SWP_NOMOVE | winUser.SWP_NOSIZE,
		)

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
			# Wait until the compositor has removed the border before reading pixels.
			windll.dwmapi.DwmFlush()
			yield
		finally:
			self._showOnTop()
