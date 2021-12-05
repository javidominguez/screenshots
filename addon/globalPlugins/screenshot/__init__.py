""" NVDA addon that provides an wizard to take screenshots

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

		if config.conf["screenshots"]["folder"] == "/":
			config.conf["screenshots"]["folder"] = os.path.join(os.getenv("USERPROFILE"), "documents")

		NVDASettingsDialog.categoryClasses.append(ScreenshotsPanel)

		self.oldGestureBindings = {}
		self.toggling = False
		self.rectangle = None

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

	def script_keyboardLayer(self, gesture):
		if self.toggling:
			self.script_exit(gesture)
			self.finish()
			return
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

	__gestures = {
	"kb:control+NVDA+escape": "keyboardLayer"
	}

	__keyboardLayerGestures = {
	"kb:upArrow": "levelUp",
	"kb:space": "rectangleInfo",
	"kb:1": "rectangleInfo",
	"kb:2": "rectangleInfo",
	"kb:enter": "saveScreenshot",
	"kb:numpadEnter": "saveScreenshot",
	# "kb:shift+rightArrow": "moveTopToRight",
	# "kb:shift+leftArrow": "moveTopToUp",
	}

	def script_levelUp(self, gesture):
		container = self.rectangle.object.container
		while container and container.location == self.rectangle.object.location:
			container = container.container
		if container:
			self.rectangle = Rectangle().fromObject(container)
			ui.message(_("Frammed {object} {name} ").format(
			object=controlTypes.role._roleLabels[container.role], name=container.name if container.role == controlTypes.Role.WINDOW else ""))
			self.script_rectangleInfo(None)
		else:
			tones.beep(100,90)

	def script_rectangleInfo(self, gesture):
		messages = (
		_("from {startX}, {startY} to {endX}, {endY}").format(
		startX=self.rectangle.location.topLeft.x, startY=self.rectangle.location.topLeft.y,
		endX=self.rectangle.location.bottomRight.x, endY=self.rectangle.location.bottomRight.y),
		_("width {w} per height {h}").format(w=self.rectangle.location.width, h=self.rectangle.location.height)
		)
		try:
			ui.message(messages[int(gesture.mainKeyName)-1])
		except:
			ui.message(". ".join(messages))

	def script_saveScreenshot(self, gesture):
		img = self.rectangle.getImage()
		filename = "screenshot_{timestamp}.{ext}".format(
		timestamp=datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
		ext=config.conf["screenshots"]["format"])
		img.SaveFile(os.path.join(config.conf["screenshots"]["folder"], filename))
		self.finish()
		if config.conf["screenshots"]["action"] == 1:
			os.startfile(os.path.join(config.conf["screenshots"]["folder"], filename))
		elif config.conf["screenshots"]["action"] == 2:
			os.startfile(config.conf["screenshots"]["folder"])

	def script_wrongGesture(self, gesture):
		tones.beep(100,50)