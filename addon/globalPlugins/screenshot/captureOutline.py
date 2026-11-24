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
		self.Bind(wx.EVT_PAINT, self._onPaint)

	def Destroy(self):
		windll.user32.RemovePropW(HWND(self.GetHandle()), "NonRudeHWND")
		return super().Destroy()

	def showFor(self, location):
		left, top, width, height = location
		if width <= 0 or height <= 0:
			self.Hide()
			return
		self.SetSize(left, top, width, height, wx.SIZE_ALLOW_MINUS_ONE)
		self._showOnTop()
		self.Refresh(False)
		self.Update()

	def _showOnTop(self):
		if not self.IsShown():
			self.ShowWithoutActivating()
		# The taskbar is topmost too. Keep the outline above it without taking focus.
		windll.user32.SetWindowPos(
			HWND(self.GetHandle()), winUser.HWND_TOPMOST, 0, 0, 0, 0,
			winUser.SWP_NOACTIVATE | winUser.SWP_NOMOVE | winUser.SWP_NOSIZE,
		)

	def _onPaint(self, event):
		dc = wx.AutoBufferedPaintDC(self)
		dc.SetBackground(wx.Brush(wx.Colour(255, 255, 0)))
		dc.Clear()
		dc.SetPen(wx.TRANSPARENT_PEN)
		width, height = self.GetClientSize()
		stroke = self.FromDIP(2)
		# Draw inward so all four edges remain visible for a full-screen selection.
		for inset, color in ((stroke, wx.BLACK), (2 * stroke, self._colorKey)):
			if width > 2 * inset and height > 2 * inset:
				dc.SetBrush(wx.Brush(color))
				dc.DrawRectangle(inset, inset, width - 2 * inset, height - 2 * inset)

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
