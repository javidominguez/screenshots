#!/1/bin/env python3
# -*- coding: UTF-8 -*-
"""
This file is covered by the GNU General Public License.
Copyright (C) Javi Dominguez 2021
"""

from threading import Event, Thread
import api
import locationHelper
import screenBitmap
import wx

EVT_object = "Rectangle.event_referenceObjectChanged"
EVT_objectInside = "Rectangle.event_referenceObjectInsideFrame"
EVT_objectOverflow = "Rectangle.event_referenceObjectOverflowFrame"
EVT_insideWindow = "Rectangle.event_rectInsideWindow"
EVT_overflowWindow = "Rectangle.event_rectOverflowWindow"

class Rectangle():
	""" Class that defines a virtual rectangle on the screen.
	This rectangle delimits the area of the screen from which a capture will be taken. """

	def __init__(self, top=0, left=0, width=0, height=0):
		self.__location = locationHelper.RectLTWH(top,left,width,height)
		self.__object = None
		self.__events = {
		EVT_object: Event(), # When the reference object changes
		EVT_objectInside: Event(), # When the reference object goes inside the rectangle
		EVT_objectOverflow: Event(), # When any part of the reference object is outside the rectangle
		EVT_insideWindow: Event(), # When the rectangle is contained in the active foreground window
		EVT_overflowWindow: Event() # When the rectangle sticks out of the active window in the foreground
		}
		self.__threads = set()

	def __del__(self):
		while self.__threads:
			self.__threads.pop().kill()

	def fromObject(self, obj):
		if not hasattr(obj, "location"): raise TypeError("The argument must be an NVDA object")
		if not isinstance(obj.location,locationHelper.RectLTWH): raise TypeError("The location attribute must be a RectLTWH object")
		self.__object = obj
		self.__location = self.__delimit_object(obj)
		return self

	def getRGBQUAD_Array(self):
		""" Returns a screenBitmap.RGBQUAD_Array object with the pixels that the rectangle contains. """
		try:
			return screenBitmap.ScreenBitmap(self.__location.width, self.__location.height).captureImage(self.__location.top, self.__location.left, self.__location.width, self.__location.height)
		except:
			return None

	def getImage(self):
		""" Returns a wx.Image object with the screen image delimited by the rectangle. """
		rgb = self.getRGBQUAD_Array()
		if not rgb: return None
		return wx.BitmapFromBufferRGBA(self.__location.width, self.__location.height, rgb).ConvertToImage()

	def moveLeftEdge(self, step=1):
		check = self.__check_overflows()
		x, y, w, h = self.__location
		x = x+step
		w = w+(-1*step)
		if x<0:
			check.set()
			return None
		if x > self.__location.right-10:
			check.set()
			return None
		self.__location = locationHelper.RectLTWH(x, y, w, h)
		self.__hook_object()
		check.set()
		return x

	def moveRightEdge(self, step=1):
		check = self.__check_overflows()
		x, y, w, h = self.__location
		w = w+step
		if x+w > api.getDesktopObject().location.width:
			check.set()
			return None
		if w < 10:
			check.set()
			return None
		self.__location = locationHelper.RectLTWH(x, y, w, h)
		self.__hook_object()
		check.set()
		return x+w

	def moveTopEdge(self, step=1):
		check = self.__check_overflows()
		x, y, w, h = self.__location
		y = y+step
		h = h+(-1*step)
		if y < 0:
			check.set()
			return None
		if y > self.__location.bottom-10:
			check.set()
			return None
		self.__location = locationHelper.RectLTWH(x,y,w,h)
		self.__hook_object()
		check.set()
		return y

	def moveBottomEdge(self, step=1):
		check = self.__check_overflows()
		x, y, w, h = self.__location
		h = h+step
		if h < 10:
			check.set()
			return None
		if y+h > api.getDesktopObject().location.height:
			check.set()
			return None
		self.__location = locationHelper.RectLTWH(x, y, w, h)
		self.__hook_object()
		check.set()
		return y+h

	def expandOrShrink(self, step=1):
		check = self.__check_overflows()
		try:
			location = api.getDesktopObject().location.intersection(self.__location.expandOrShrink(step))
		except:
			check.set()
			return False
		if location.width < 10 or location.height < 10:
			check.set()
			return False
		elif location == self.__location:
			check.set()
			return False
		else:
			self.__location = location
			check.set()
			return True

	def ratioObjectFrame(self, obj):
		if not hasattr(obj, "location"): raise TypeError("The argument must be an NVDA object")
		if not isinstance(obj.location,locationHelper.RectLTWH): raise TypeError("The location attribute must be a RectLTWH object")
		objloc = self.__location.intersection(self.__delimit_object(obj))
		return (objloc.width*objloc.height)/(self.__location.width*self.__location.height)

	def ratioFrameObject(self, obj):
		if not hasattr(obj, "location"): raise TypeError("The argument must be an NVDA object")
		if not isinstance(obj.location,locationHelper.RectLTWH): raise TypeError("The location attribute must be a RectLTWH object")
		objloc = self.__delimit_object(obj)
		return (self.__location.width*self.__location.height)/(objloc.width*objloc.height)

	def isObjectInsideRectangle(self, obj=None):
		if not obj: obj = self.__object
		if not hasattr(obj, "location"): raise TypeError("The argument must be an NVDA object")
		if not isinstance(obj.location,locationHelper.RectLTWH): raise TypeError("The location attribute must be a RectLTWH object")
		return self.__location.isSuperset(self.__delimit_object(obj))

	def isRectangleInsideTheWindow(self):
		return self.__delimit_object(api.getForegroundObject()).isSuperset(self.__location)

	def adjustToObject(self):
		if not self.__object: return False
		self.__location = self.__delimit_object(self.__object)
		return True

	def bind(self, event, func, *args, **kwargs):
		""" Binds an event with a function that will be executed when the event set. """
		if event not in self.__events: raise TypeError("unexpected type. The first argument expected a valid rectangle event.")
		if not hasattr(func, "__call__"): raise TypeError("Unexpected type. The second argument expected a function or a callable object.")
		thread = EventHandler(self.__events[event], func, *args, **kwargs)
		thread.setName(event)
		self.__events[event].clear()
		thread.start()
		self.__threads.add(thread)

	def __hook_object(self):
		""" Find the most appropriate object to be the reference object for the rectangle.
		It will be the most centered object, in the foreground and occupying a larger area. """
		x, y = self.__location.center
		obj = api.getDesktopObject().objectFromPoint(x,y)
		if not self.__object or (
		obj != self.__object and\
		self.ratioObjectFrame(obj) >= self.ratioObjectFrame(self.__object)) or (
		obj != self.__object and self.isObjectInsideRectangle(obj) and not self.isObjectInsideRectangle()):
			self.__object = obj
			self.__events[EVT_object].set()

	def __delimit_object(self, obj):
		""" Set  the limits of the object taking into account only the part included  in its successive container objects.
		The part that is outside these limits will most likely not be displayed on the screen..
		Returns an object locationHelper.RectLTWH. """
		if not hasattr(obj, "location"): raise TypeError("The argument must be an NVDA object")
		if not isinstance(obj.location,locationHelper.RectLTWH): raise TypeError("The location attribute must be a RectLTWH object")
		location = obj.location
		while obj:
			obj = obj.container
			if obj: location = location.intersection(obj.location)
		return location

	def __check_overflows(self):
		""" Save the state of the object and the window with respect to the rectangle,
		then it starts a thread that will wait for the termination of the method that called it, when it receives the signal it will check if the states have changed and it will set the corresponding events.
		Returns an event that is received by the method that called it, which will set it when necessary which will send the signal to start the thread. """
		ev = Event()
		obj = self.__object
		insideObject = self.isObjectInsideRectangle()
		insideWindow = self.isRectangleInsideTheWindow()
		def check():
			ev.wait(1.0)
			if not ev.isSet:
			# If it get here because  timeout was exceeded, it exits without doing anything.
				return
			if self.__object != obj: return
			curInsideObject = self.isObjectInsideRectangle()
			if (insideObject, curInsideObject) == (True, False):
				self.__events[EVT_objectOverflow].set()
			elif (insideObject, curInsideObject) == (False, True):
				self.__events[EVT_objectInside].set()
			curInsideWindow = self.isRectangleInsideTheWindow()
			if (insideWindow, curInsideWindow) == (True, False):
				self.__events[EVT_overflowWindow].set()
			elif (insideWindow, curInsideWindow) == (False, True):
				self.__events[EVT_insideWindow].set()
		Thread(target=check).start()
		return ev

	@property
	def object(self):
		return self.__object

	@property
	def location(self):
		return self.__location

	@property
	def top(self):
		return self.__location.top

	@property
	def left(self):
		return self.__location.left

	@property
	def height(self):
		return self.__location.height

	@property
	def width(self):
		return self.__location.width

	@property
	def right(self):
		return self.__location.right

	@property
	def bottom(self):
		return self.__location.bottom

	@property
	def topLeft(self):
		return self.__location.topLeft

	@property
	def topRight(self):
		return self.__location.topRight

	@property
	def bottomLeft(self):
		return self.__location.bottomLeft

	@property
	def bottomRight(self):
		return self.__location.bottomRight

class EventHandler(Thread):
	""" Thread that listens for an event and executes a function each time it receives the signal. """

	def __init__(self, event, func, *args, **kwargs):
		self.__event = event
		self.__action = func
		self.__args = args
		self.__kwargs = kwargs
		self.__flag = True
		super(EventHandler, self).__init__()
		self.daemon = True

	def run(self):
		while self.__flag:
			self.__event.wait()
			if self.__flag:
				self.__action(*self.__args, **self.__kwargs)
			self.__event.clear()

	def kill(self):
		self.__flag = False
		self.__event.set()
