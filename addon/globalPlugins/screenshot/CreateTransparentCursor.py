import wx

image = wx.Image(45,50)
image.SetAlpha(b'\x00' * 45 * 50)
image.SaveFile("TransparentCursor.cur")