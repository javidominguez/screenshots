#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
This file is covered by the GNU General Public License.
Copyright (C) Javi Dominguez 2021
"""

import api
import wx
import screenBitmap
import locationHelper

class Rectangle():
	def __init__(self, top=0, left=0, width=0, height=0):
		self.location = locationHelper.RectLTWH(top,left,width,height)
		self.object = None

	def fromObject(self, obj):
		if not hasattr(obj, "location"): raise TypeError("The argument must be an NVDA object")
		if not isinstance(obj.location,locationHelper.RectLTWH): raise TypeError("The location attribute must be a RectLTWH object")
		self.object = obj
		location = self.object.location
		obj = self.object
		while obj:
			obj = obj.container
			if obj: location = location.intersection(obj.location)
		self.location = location
		return self

	def getRGBQUAD_Array(self):
		if not self.object: return None
		return screenBitmap.ScreenBitmap(self.location.width, self.location.height).captureImage(self.location.top, self.location.left, self.location.width, self.location.height)

	def getImage(self):
		rgb = self.getRGBQUAD_Array()
		if not rgb: return None
		return wx.BitmapFromBufferRGBA(self.location.width, self.location.height, rgb).ConvertToImage()

	def moveLeftEdge(self, step=1):
		x, y, w, h = self.location
		x = x+step
		w = w+(-1*step)
		if x<0: return None
		if x > self.location.right-10: return None
		self.location = locationHelper.RectLTWH(x, y, w, h)
		return x

	def moveRightEdge(self, step=1):
		x, y, w, h = self.location
		w = w+step
		if x+w > api.getDesktopObject().location.width: return None
		if w < 10: return None
		self.location = locationHelper.RectLTWH(x, y, w, h)
		return x+w

	def moveTopEdge(self, step=1):
		x, y, w, h = self.location
		y = y+step
		h = h+(-1*step)
		if y < 0: return None
		if y > self.location.bottom-10: return None
		self.location = locationHelper.RectLTWH(x,y,w,h)
		return y

	def moveBottomEdge(self, step=1):
		x, y, w, h = self.location
		h = h+step
		if h < 10: return None
		if y+h > api.getDesktopObject().location.height: return None
		self.location = locationHelper.RectLTWH(x, y, w, h)
		return y+h
