#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
NVDA addon that provides an wizard to take screenshots

This file is covered by the GNU General Public License.
Copyright (C) Javi Dominguez 2021
"""

import globalPluginHandler
from keyboardHandler import KeyboardInputGesture
from functools import wraps
import tones
import ui
import os
import wx
import api
import controlTypes
import config
import vision
from datetime import datetime
from .rectangleHandler import Rectangle
from .gui import *

def finally_(func, final):
	"""Calls final after func, even if it fails."""
	def wrap(f):
		@wraps(f)
		def new(*args, **kwargs):
			try:
				func(*args, **kwargs)
			finally:
				final()
		return new
	return wrap(final)

confspec = {
	"folder":"string(default=/)",
	"format":"string(default=BMP)",
	"action":"integer(default=2)",
	"step":"integer(default=5)"
}
config.conf.spec["screenshots"]=confspec

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)

		# By default, the user's documents folder is assumed as the folder where to save the image files of the screenshots.
		try:
		# Read the normal profile settings
			folder = config.conf.profiles[0]["screenshots"]["folder"]
		except:
			# If it is not possible we read it from the general configuration
			folder = config.conf["screenshots"]["folder"]
		if folder == "/":
		# If it is used for the first time there will be no folder assigned. The user's documents is assigned to the normal profile.
			try:
				config.conf.profiles[0]["screenshots"]["folder"] = os.path.join(os.getenv("USERPROFILE"), "documents")
			except KeyError:
				if "screenshots" not in config.conf.profiles[0]:
					config.conf.profiles[0]["screenshots"] = config.conf["screenshots"]
				config.conf.profiles[0]["screenshots"]["folder"] = os.path.join(os.getenv("USERPROFILE"), "documents")

		NVDASettingsDialog.categoryClasses.append(ScreenshotsPanel)

		self.oldGestureBindings = {}
		self.toggling = False
		self.rectangle = None
		self.oldRectangles = Stack()
		self.lastGesture = None

	def terminate(self):
		try:
			NVDASettingsDialog.categoryClasses.remove(ScreenshotsPanel)
		except:
			pass

	def getScript(self, gesture):
		if not self.toggling:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		script = globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if not script:
			if "kb:escape" in gesture.identifiers:
				script = finally_(self.script_exit, self.finish)
			else:
				script = finally_(self.script_wrongGesture, lambda: None) 
		return script

	def script_exit(self, gesture):
		ui.message("Cancelled")

	def finish(self):
		self.toggling = False
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		for key in self.oldGestureBindings:
			script = self.oldGestureBindings[key]
			if hasattr(script.__self__, script.__name__):
				script.__self__.bindGesture(key, script.__name__[7:])
		self.rectangle = None
		self.oldRectangles.clear()
		self.lastGesture = None

	def script_keyboardLayer(self, gesture):
		if self.toggling:
			self.script_exit(gesture)
			self.finish()
			return
		self.lastGesture = gesture.identifiers
		from visionEnhancementProviders.screenCurtain import ScreenCurtainProvider
		screenCurtainId = ScreenCurtainProvider.getSettings().getId()
		screenCurtainProviderInfo = vision.handler.getProviderInfo(screenCurtainId)
		isScreenCurtainRunning = bool(vision.handler.getProviderInstance(screenCurtainProviderInfo))
		if isScreenCurtainRunning:
			# Translators: Reported when screen curtain is enabled.
			ui.message(_("Please disable screen curtain before take a screenshot"))
			return
		for k in [i[3:] for i in self.__keyboardLayerGestures]:
			try:
				script = KeyboardInputGesture.fromName(k).script
			except KeyError:
				script = None
			if script and self != script.__self__:
				try:
					script.__self__.removeGestureBinding("kb:"+k)
				except KeyError:
					pass
				else:
					self.oldGestureBindings["kb:"+k] = script
		self.bindGestures(self.__keyboardLayerGestures)
		self.toggling = True
		navObject = api.getNavigatorObject()
		self.rectangle = Rectangle().fromObject(navObject)
		ui.message(_("Frammed {object} {name} ").format(
		object=controlTypes.role._roleLabels[navObject.role], name=navObject.name if navObject.role == controlTypes.Role.WINDOW else ""))
		self.script_rectangleInfo(None)
	script_keyboardLayer.__doc__ = _("Launch the screenshots wizard. A layer of keyboard commands will be activated. Use enter key to take a screenshot, escape to cancel. See documentation for know more commands.")
	__gestures = {
	"kb:printScreen": "keyboardLayer"
	}

	__keyboardLayerGestures = {
	"kb:upArrow": "levelUp",
	"kb:downArrow": "goBack",
	"kb:space": "rectangleInfo",
	"kb:pageUp": "increaseStep",
	"kb:pageDown": "decreaseStep",
	"kb:1": "rectangleInfo",
	"kb:2": "rectangleInfo",
	"kb:3": "rectangleInfo",
	"kb:4": "rectangleInfo",
	"kb:5": "rectangleInfo",
	"kb:6": "rectangleInfo",
	"kb:7": "rectangleInfo",
	"kb:enter": "saveScreenshot",
	"kb:numpadEnter": "saveScreenshot",
	"kb:shift+rightArrow": "shrinkLeft",
	"kb:shift+leftArrow": "expandLeftward",
	"kb:shift+upArrow": "expandUpward",
	"kb:shift+downArrow": "shrinkAbove",
	"kb:control+rightArrow": "expandRightward",
	"kb:control+leftArrow": "shrinkRight",
	"kb:control+upArrow": "shrinkBottom",
	"kb:control+downArrow": "expandBottomward"
	}

	def script_levelUp(self, gesture):
		self.lastGesture = gesture.identifiers
		container = self.rectangle.object.container
		while container and container.location == self.rectangle.object.location:
			container = container.container
		if container:
			self.oldRectangles.push(self.rectangle)
			self.rectangle = Rectangle().fromObject(container)
			ui.message(_("Frammed {object} {name} ").format(
			object=controlTypes.role._roleLabels[container.role], name=container.name if container.name and container.role == controlTypes.Role.WINDOW else ""))
			self.script_rectangleInfo(None)
		else:
			tones.beep(100,90)

	def script_goBack(self, gesture):
		self.lastGesture = gesture.identifiers
		if self.oldRectangles.isEmpty():
			self.script_wrongGesture(None)
			return
		self.rectangle = self.oldRectangles.pop()
		ui.message(_("Frammed {object} {name} ").format(
		object=controlTypes.role._roleLabels[self.rectangle.object.role], name=self.rectangle.object.name if self.rectangle.object.name and self.rectangle.object.role == controlTypes.Role.WINDOW else ""))
		self.script_rectangleInfo(None)

	def script_rectangleInfo(self, gesture):
		self.lastGesture = None
		messages = (
		# 1
		_("from {startX}, {startY} to {endX}, {endY}").format(
		startX=self.rectangle.location.topLeft.x, startY=self.rectangle.location.topLeft.y,
		endX=self.rectangle.location.bottomRight.x, endY=self.rectangle.location.bottomRight.y),
		# 2
		_("width {w} per height {h}").format(w=self.rectangle.location.width, h=self.rectangle.location.height),
		# 3
		_("The reference object is {objectRole} {objectName}").format(
		objectRole = controlTypes.role._roleLabels[self.rectangle.object.role],
		objectName = self.rectangle.object.name if self.rectangle.object.name else ""),
		# 4
		_("{ratio}% of the rectangle is occupied by the object of reference").format(
		ratio=round(self.rectangle.ratioObjectFrame(self.rectangle.object)*100)),
		# 5
		"{msg}".format(
		msg = _("The reference object is completely inside the rectangle") if self.rectangle.isObjectInsideRectangle() else _("Part of the reference object is outside the rectangle")),
		# 6
		"{msg}".format(
		msg = _("The rectangle is inside the active window") if self.rectangle.isRectangleInsideTheWindow() else _("Part of the rectangle is outside the active window")),
		# 7
		_("The rectangle occupies {percentage}% of the screen").format(
		percentage = round(self.rectangle.ratioFrameObject(api.getDesktopObject())*100))
		)
		try:
			ui.message(messages[int(gesture.mainKeyName)-1])
		except:
			ui.message(". ".join(messages))

	def script_saveScreenshot(self, gesture):
		img = self.rectangle.getImage()
		filename = "screenshot_{timestamp}.{ext}".format(
		timestamp=datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
		ext=config.conf.profiles[0]["screenshots"]["format"])
		img.SaveFile(os.path.join(config.conf.profiles[0]["screenshots"]["folder"], filename))
		self.finish()
		if config.conf.profiles[0]["screenshots"]["action"] == 1:
			os.startfile(os.path.join(config.conf.profiles[0]["screenshots"]["folder"], filename))
		elif config.conf.profiles[0]["screenshots"]["action"] == 2:
			os.startfile(config.conf.profiles[0]["screenshots"]["folder"])

	def script_increaseStep(self, gesture):
		self.increaseOrDecreaseStep(1)
		self.lastGesture = gesture.identifiers

	def script_decreaseStep(self, gesture):
		self.increaseOrDecreaseStep(-1)
		self.lastGesture = gesture.identifiers

	def increaseOrDecreaseStep(self, x):
		step = int(config.conf.profiles[0]["screenshots"]["step"])
		step = step+x
		if step < 11 and step > 0:
			config.conf.profiles[0]["screenshots"]["step"] = step
			# Translators: Message   when modifying the amount of movement in pixels
			ui.message(_("{step} px").format(step=config.conf.profiles[0]["screenshots"]["step"]))
		else:
			self.script_wrongGesture(None)

	def script_expandUpward(self, gesture):
		p = self.rectangle.moveTopEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Top edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkAbove(self, gesture):
		p = self.rectangle.moveTopEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Top edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandLeftward(self, gesture):
		p = self.rectangle.moveLeftEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Left edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkLeft(self, gesture):
		p = self.rectangle.moveLeftEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Left edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandBottomward(self, gesture):
		p = self.rectangle.moveBottomEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Bottom edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkBottom(self, gesture):
		p = self.rectangle.moveBottomEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Bottom edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandRightward(self, gesture):
		p = self.rectangle.moveRightEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Right edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkRight(self, gesture):
		p = self.rectangle.moveRightEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			msg="" if self.lastGesture==gesture.identifiers else _("Right edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_wrongGesture(self, gesture):
		self.lastGesture = None
		tones.beep(100,50)

class Stack:
	def __init__(self):
		self.items = []

	def isEmpty(self):
		return not self.items

	def push(self, item):
		self.items.insert(0, item)

	def pop(self):
		if self.isEmpty():
			return None
		else:
			return self.items.pop(0)

	def clear(self):
		self.items = []
		return self.isEmpty()
