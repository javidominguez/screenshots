#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
NVDA addon that provides an wizard to take screenshots

This file is covered by the GNU General Public License.
Copyright (C) Javi Dominguez 2021
"""

from .gui import *
from .rectangleHandler import *
from contentRecog import uwpOcr, RecogImageInfo
from datetime import datetime
from functools import wraps
from keyboardHandler import KeyboardInputGesture
from subprocess import Popen
from threading import Event, Thread, Timer
from time import sleep
from tones import beep, nvwave
import addonHandler
import api
import braille
import config
import controlTypes
import globalCommands
import globalPluginHandler
import globalVars
import gui
import inputCore
import mouseHandler
import os
import scriptHandler
import ui
import vision
import winInputHook
import winUser
import wx

addonHandler.initTranslation()

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

def evtMessage(msg):
	try:
		nvwave.playWaveFile(os.path.join(os.path.dirname(__file__), "soundEfects", "event.wav"))
	except:
		pass
	ui.message(msg)

confspec = {
	"folder":"string(default=/)",
	"format":"string(default=BMP)",
	"action":"integer(default=2)",
	"step":"integer(default=5)",
	"scale":"boolean(default=false)"
}
config.conf.spec["screenshots"]=confspec
mouseCallbackFunc = None

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("Screenshots Wizard")

	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		if globalVars.appArgs.secure == True:
			raise RuntimeError("This add-on cannot run on secure screens")

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
					config.conf.profiles[0]["screenshots"] = {}
					for k in config.conf["screenshots"]:
						config.conf.profiles[0]["screenshots"][k] = config.conf["screenshots"][k]
				config.conf.profiles[0]["screenshots"]["folder"] = os.path.join(os.getenv("USERPROFILE"), "documents")
		if "scale" not in config.conf.profiles[0]["screenshots"]:
		# Required for those upgrading from previous versions.
			config.conf.profiles[0]["screenshots"]["scale"] = config.conf["screenshots"]["scale"]

		NVDASettingsDialog.categoryClasses.append(ScreenshotsPanel)

		self.oldGestureBindings = {}
		self.toggling = False
		self.rectangle = Rectangle()
		self.oldRectangles = Stack()
		self.lastGesture = None
		#14233
		self.brailleMessageTimeout = config.conf["braille"]["showMessages"] if "showMessages" in config.conf["braille"] else config.conf["braille"]["noMessageTimeout"]
		self.allowedBrailleGestures = set()
		self.allowedNavigationGestures = set()
		self.kbTimer = None
		self.brTimer = None
		self.flagNoAction = False
		self.lastScreenshot = None
		self.recognizer = uwpOcr.UwpOcr()

	def terminate(self):
		try:
			NVDASettingsDialog.categoryClasses.remove(ScreenshotsPanel)
		except:
			pass

	def mouseCapture(self, msg, x, y, injected):
		if msg  == mouseHandler.WM_MOUSEMOVE:
			return mouseCallbackFunc(msg, x, y, injected)
		else:
			self.script_wrongGesture(None)

	def lockMouse(self):
		global mouseCallbackFunc
		mouseCallbackFunc = winInputHook.mouseCallback
		winInputHook.setCallbacks(mouse=self.mouseCapture)
		
	def unlockMouse(self):
		global mouseCallbackFunc
		winInputHook.setCallbacks(mouse=mouseCallbackFunc)
		mouseCallbackFunc = None

	def getScript(self, gesture):
		if not self.toggling:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if True in [gID.lower() in self.allowedBrailleGestures for gID in gesture.identifiers] \
		or set(gesture.normalizedIdentifiers) & self.allowedNavigationGestures:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if isinstance(gesture, KeyboardInputGesture) and gesture.mainKeyName != "f1" and self.kbTimer:
			self.kbTimer = None
		script = globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		inputCore.manager._captureFunc = lambda self: not (gesture.isModifier and gesture.mainKeyName in (
		"leftWindows", "rightWindows", "leftAlt"))
		if not script:
			if "kb:escape" in gesture.identifiers:
				script = finally_(self.script_exit, self.finish)
			else:
				script = finally_(self.script_wrongGesture, lambda: None) 
		return script

	def script_exit(self, gesture):
		# Translators: Message when escape is pressed to exit the keyboard command layer
		if "showMessages" in config.conf["braille"]:
			#14233
			config.conf["braille"]["showMessages"] = self.brailleMessageTimeout
		else:
			config.conf["braille"]["noMessageTimeout"] = self.brailleMessageTimeout
		# Translators: Message presented when leaving the keyboard  layer
		ui.message(_("Cancelled"))

	def finish(self):
		self.toggling = False
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		for key in self.oldGestureBindings:
			script = self.oldGestureBindings[key]
			if hasattr(script.__self__, script.__name__):
				script.__self__.bindGesture(key, script.__name__[7:])
		self.rectangle = Rectangle()
		self.oldRectangles.clear()
		self.unlockMouse()
		self.lastGesture = None

	def script_keyboardLayer(self, gesture):
		if self.toggling:
			self.script_wrongGesture(None)
			return
		from visionEnhancementProviders.screenCurtain import ScreenCurtainProvider
		screenCurtainId = ScreenCurtainProvider.getSettings().getId()
		screenCurtainProviderInfo = vision.handler.getProviderInfo(screenCurtainId)
		isScreenCurtainRunning = bool(vision.handler.getProviderInstance(screenCurtainProviderInfo))
		if isScreenCurtainRunning:
			# Translators: Reported when screen curtain is enabled.
			ui.message(_("Please disable screen curtain before take a screenshot"))
			return
		self.lastGesture = gesture.identifiers
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
		try:
			gestures = inputCore.manager.getAllGestureMappings(obj=gui.mainFrame.prevFocus, ancestors=gui.mainFrame.prevFocusAncestors)
		except:
			gestures = None
		try:
		# Braille gestures that will be allowed:
			for brGesture in\
			gestures[globalCommands.SCRCAT_BRAILLE][globalCommands.GlobalCommands.script_braille_scrollForward.__doc__].gestures\
			+ gestures[globalCommands.SCRCAT_BRAILLE][globalCommands.GlobalCommands.script_braille_scrollBack.__doc__].gestures:
				self.allowedBrailleGestures.add(brGesture)
		except:
			pass
		try:
		# Object navigation gestures will be allowed
			for x in gestures:
				for y in gestures[x]:
					gestureScriptInfo = gestures[x][y]
					if gestureScriptInfo.className == "GlobalCommands" and (
					gestureScriptInfo.scriptName.startswith("navigatorObject_") \
					and not gestureScriptInfo.scriptName.endswith("devInfo")):
						for g in gestureScriptInfo.gestures:
							self.allowedNavigationGestures.add(g)
		except:
			pass
		self.toggling = True
		self.lockMouse()
		if "showMessages" in config.conf["braille"]:
			#14233
			config.conf["braille"]["showMessages"] = 2
		else:
			config.conf["braille"]["noMessageTimeout"] = True
		focus = api.getFocusObject()
		try:
			self.rectangleFromObject(focus)
		except:
			try:
				self.rectangleFromObject(api.getForegroundObject())
			except:
				self.rectangleFromObject(api.getDesktopObject())
	# Translators: Message presented in input help mode.
	script_keyboardLayer.__doc__ = _("Launch the screenshots wizard. A layer of keyboard commands will be activated. Use enter key to take a screenshot, escape to cancel. See documentation for know more commands.")

	def script_openFolder(self, gesture):
		try:
			os.startfile(config.conf.profiles[0]["screenshots"]["folder"])
		except FileNotFoundError:
			Thread(target=wx.MessageBox, args=(
			config.conf.profiles[0]["screenshots"]["folder"], _("Folder not found"), wx.ICON_EXCLAMATION)
			).start()
	# Translators: Message presented in input help mode.
	script_openFolder.__doc__ = _("Open the folder where the screenshots are stored.")

	def script_openLastScreenshot(self, gesture):
		if not self.lastScreenshot:
			ui.message(_("No screenshot has been taken yet."))
			return
		try:
			os.startfile(self.lastScreenshot)
		except FileNotFoundError:
			Thread(target=wx.MessageBox, args=(
			self.lastScreenshot, _("File not found"), wx.ICON_EXCLAMATION)
			).start()
	# Translators: Message presented in input help mode.
	script_openLastScreenshot.__doc__ = _("Open the last screenshot file in the default app.")

	def script_instantShotFullscreen(self, gesture):
		self.instantShot(api.getDesktopObject())
	# Translators: Message presented in input help mode.
	script_instantShotFullscreen.__doc__ = _("Take a full screenshot directly, bypassing the keyboard command layer")

	def script_instantShotFocus(self, gesture):
		self.instantShot(api.getFocusObject())
	# Translators: Message presented in input help mode.
	script_instantShotFocus.__doc__ = _("Take a  screenshot of focused object directly, bypassing the keyboard command layer")

	def script_instantShotWindow(self, gesture):
		self.instantShot(api.getForegroundObject())
	# Translators: Message presented in input help mode.
	script_instantShotWindow.__doc__ = _("Take a  screenshot of current window directly, bypassing the keyboard command layer")

	def instantShot(self, obj):
		if self.toggling:
			self.script_wrongGesture(None)
			return
		from visionEnhancementProviders.screenCurtain import ScreenCurtainProvider
		screenCurtainId = ScreenCurtainProvider.getSettings().getId()
		screenCurtainProviderInfo = vision.handler.getProviderInfo(screenCurtainId)
		isScreenCurtainRunning = bool(vision.handler.getProviderInstance(screenCurtainProviderInfo))
		if isScreenCurtainRunning:
			# Translators: Reported when screen curtain is enabled.
			ui.message(_("Please disable screen curtain before take a screenshot"))
			return
		self.rectangleFromObject(obj, verbose=False)
		self.flagNoAction = True
		self.script_saveScreenshot(None)
		self.flagNoAction = False

	def script_levelUp(self, gesture):
		self.lastGesture = gesture.identifiers
		if self.rectangle.location == api.getDesktopObject().location:
			container = None
		else:
			container = self.rectangle.object.container
		while container and container.location == self.rectangle.object.location:
			container = container.container
		if container and container.location == (0,0,0,0):
			container = container.container
		if container:
			self.rectangleFromObject(container)
		else:
			beep(100,50)
			# Translators: Message when rying to frame the containing object but the largest container is already framed
			ui.message(_("There is no upper container"))

	def script_frameObject(self, gesture):
		self.lastGesture = gesture.identifiers
		if gesture.mainKeyName == "w":
			obj = api.getForegroundObject()
		elif gesture.mainKeyName == "s":
			obj = api.getDesktopObject()
		elif gesture.mainKeyName == "f":
			obj = api.getFocusObject()
		elif gesture.mainKeyName == "n":
			obj = api.getNavigatorObject()
		elif gesture.mainKeyName == "m":
			x, y = winUser.getCursorPos()
			obj = api.getDesktopObject().objectFromPoint(x,y)
		else:
			self.script_wrongGesture(None)
			return
		if obj == self.rectangle.object:
			beep(100,50)
			# Translators: Message presented when trying to frame an object that is already framed.
			ui.message(_("Already framed"))
		elif obj.location.width == 0 or obj.location.height == 0:
			beep(100, 50)
			# Translators: Message presented when the size of the object is 0 and therefore cannot be framed.
			ui.message(_("The object cannot be framed."))
		else:
			self.rectangleFromObject(obj)

	def script_goBack(self, gesture):
		self.lastGesture = gesture.identifiers
		if self.oldRectangles.isEmpty():
			self.script_wrongGesture(None)
			return
		self.rectangle = self.oldRectangles.pop()
		# Translators: Message presented when a object is framed.
		ui.message(_("Frammed {object} {name} ").format(
		object=controlTypes.role._roleLabels[self.rectangle.object.role], name=self.rectangle.object.name if self.rectangle.object.name and self.rectangle.object.role == controlTypes.Role.WINDOW else ""))
		self.script_rectangleInfo(None)

	def script_rectangleInfo(self, gesture):
		self.lastGesture = None
		messages = (
		# 1
		# Translators: Rectangle information: coordinates of the upper left and lower right corners.
		_("from {startX}, {startY} to {endX}, {endY}").format(
		startX=self.rectangle.topLeft.x, startY=self.rectangle.topLeft.y,
		endX=self.rectangle.bottomRight.x, endY=self.rectangle.bottomRight.y),
		# 2
		# Translators: Rectangle information: Rectangle dimensions, width per height.
		_("width {w} per height {h}").format(w=self.rectangle.width, h=self.rectangle.height),
		# 3
		# Translators: Rectangle information: Description of the reference object.
		_("The reference object is {objectRole} {objectName}").format(
		objectRole = controlTypes.role._roleLabels[self.rectangle.object.role],
		objectName = self.rectangle.object.name if self.rectangle.object.name else ""),
		# 4
		# Translators: Rectangle information: Proportion of the rectangle occupied by the reference object.
		_("{ratio}% of the rectangle is occupied by the object of reference").format(
		ratio=round(self.rectangle.ratioObjectFrame(self.rectangle.object)*100)),
		# 5
		# Translators: Rectangle information: Relation of the object with respect to the rectangle.
		"{msg}".format(
		msg = _("The reference object is completely inside the rectangle") if self.rectangle.isObjectInsideRectangle() else _("Part of the reference object is outside the rectangle")),
		# 6
		# Translators: Rectangle information: Relation of the rectangle with respect to the active window.
		"{msg}".format(
		msg = _("The rectangle is inside the active window") if self.rectangle.isRectangleInsideTheWindow() else _("Part of the rectangle is outside the active window")),
		# 7
		# Translators: Rectangle Information: Relation of the rectangle with respect to the screen.
		_("The rectangle occupies {percentage}% of the screen").format(
		percentage = round(self.rectangle.ratioFrameObject(api.getDesktopObject())*100))
		)
		try:
			ui.message(messages[int(gesture.mainKeyName)-1])
		except IndexError:
			self.script_wrongGesture(None)
		except:
			ui.message(". ".join(messages))

	def script_saveScreenshot(self, gesture):
		img = self.rectangle.getImage()
		if config.conf.profiles[0]["screenshots"]["scale"]:
			img = self.scaleImage(img)
		try:
			nvwave.playWaveFile(os.path.join(os.path.dirname(__file__), "soundEfects", "takeImage.wav"))
		except:
			pass
		filename = _("screenshot_{timestamp}.{ext}").format(
		timestamp=datetime.now().strftime("%d-%m-%Y_%H-%M-%S"),
		ext=config.conf.profiles[0]["screenshots"]["format"])
		def callback(result):
			if result == wx.ID_OK:
				path = dlg.GetPath()
			elif result == -1:
				path = os.path.join(config.conf.profiles[0]["screenshots"]["folder"], filename)
			else:
				wx.MessageBox(_("Image was not saved"), _("Cancelled"), wx.OK|wx.ICON_WARNING)
				return
			if img.SaveFile(path):
				self.lastScreenshot = path
			if self.flagNoAction: return
			if int(config.conf.profiles[0]["screenshots"]["action"]) == 1:
				os.startfile(path)
			elif int(config.conf.profiles[0]["screenshots"]["action"]) == 2:
				Popen("explorer /n, /select,\"{}\"".format(path))
		if gesture and "shift" in gesture.modifierNames:
			dlg = wx.FileDialog(
			parent = gui.mainFrame,
			message = _("Save image"),
			defaultDir = config.conf.profiles[0]["screenshots"]["folder"],
			defaultFile = filename,
			wildcard = "|*.bmp||*.jpg||*.gif||*.png||*.tiff",
			style = wx.FD_SAVE)
			self.finish()
			gui.runScriptModalDialog(dlg, callback)
		else:
			self.finish()
			callback(-1)

	def script_increaseStep(self, gesture):
		self.increaseOrDecreaseStep(1)
		self.lastGesture = gesture.identifiers

	def script_decreaseStep(self, gesture):
		self.increaseOrDecreaseStep(-1)
		self.lastGesture = gesture.identifiers

	def script_expandUpward(self, gesture):
		p = self.rectangle.moveTopEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the top edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Top edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkAbove(self, gesture):
		p = self.rectangle.moveTopEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the top edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Top edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandLeftward(self, gesture):
		p = self.rectangle.moveLeftEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the left edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Left edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkLeft(self, gesture):
		p = self.rectangle.moveLeftEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the left edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Left edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandBottomward(self, gesture):
		p = self.rectangle.moveBottomEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the bottom edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Bottom edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkBottom(self, gesture):
		p = self.rectangle.moveBottomEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the bottom edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Bottom edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandRightward(self, gesture):
		p = self.rectangle.moveRightEdge(int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the right edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Right edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkRight(self, gesture):
		p = self.rectangle.moveRightEdge(-1*int(config.conf.profiles[0]["screenshots"]["step"]))
		if p:
			ui.message("{msg} {point}".format(
			# Translators: Message informing that the right edge has been moved.
			msg="" if self.lastGesture==gesture.identifiers else _("Right edge moved to"),
			point=p))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_expandRectangle(self, gesture):
		if self.rectangle.expandOrShrink(int(config.conf.profiles[0]["screenshots"]["step"])):
			# Translators: Message when the rectangle is expanded, dimensions width per height
			ui.message(_("{msg} {width} per {height}").format(
			msg = _("Expanding, ") if self.lastGesture != gesture.identifiers else "",
			width = self.rectangle.width,
			height = self.rectangle.height))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_shrinkRectangle(self, gesture):
		if self.rectangle.expandOrShrink(-1*int(config.conf.profiles[0]["screenshots"]["step"])):
			# Translators: Message when the rectangle is shrunken, dimensions width per height
			ui.message(_("{msg} {width} per {height}").format(
			msg = _("Shrinking, ") if self.lastGesture != gesture.identifiers else "",
			width = self.rectangle.width,
			height = self.rectangle.height))
		else:
			self.script_wrongGesture(None)
		self.lastGesture = gesture.identifiers

	def script_adjustToObject(self, gesture):
		loc = self.rectangle.location
		if self.rectangle.adjustToObject():
			if loc == self.rectangle.location:
				beep(100,50)
				# Translators: Message when trying to fit the frame around an object that is already wrapped.
				ui.message(_("Already adjusted"))
			else:
				# Translators: Message when fit the frame  around the object.
				ui.message(_("Rectangle  adjusted to {objectRole} {objectName}").format(
				objectRole = controlTypes.role._roleLabels[self.rectangle.object.role],
				objectName = self.rectangle.object.name if self.rectangle.object.name else ""))
		else:
			self.script_wrongGesture(None)

	def script_OCR(self, gesture):
		l, t, w, h = self.rectangle.location
		self.recognizer._onResult = None
		bm = self.rectangle.getRGBQUAD_Array()
		imgInfo = RecogImageInfo.createFromRecognizer(l, t, w, h, self.recognizer)
		def onResult(r):
			ui.message(r.makeTextInfo(self.rectangle.object, "all").text)
		try:
			self.recognizer.recognize(bm, imgInfo, onResult)
		except:
			self.recognizer._onResult = None
			ui.message(_("could not be recognized. {reason}").format(
			reason = _("The image is too small.") if w<100 or h<100 else ""))

	def script_help(self, gesture):
		if self.kbTimer and self.kbTimer.isAlive():
			try:
				path = filter(lambda a: a.name == "screenshots", addonHandler.getAvailableAddons()).__next__().getDocFilePath()
				os.startfile(path)
				self.finish()
			except:
				pas
			return
		self.kbTimer = Thread(target=sleep, args=(0.35, ))
		self.kbTimer.start()
		# Translators: Help message presented when F1 is pressed on the keyboard layer.
		ui.message(_("Press up arrow to frame the container object, space bar or numbers to know the rectangle information, enter key to take the screenshot or escape to cancel and exit. See the documentation for more commands."))

	def script_wrongGesture(self, gesture):
		self.lastGesture = None
		beep(100,50)
		# Translators: Message presented, only on the braille display, when a key with no assigned script is pressed on the keyboard layer.
		wrongGestureMessage =  _("Wrong gesture")
		displayedMessage = braille.handler.messageBuffer.rawText
		if wrongGestureMessage != displayedMessage:
			braille.handler.message(wrongGestureMessage)
			if self.brTimer and self.brTimer.isAlive(): return
			def restoreDisplayedMessage():
				if braille.handler.messageBuffer.rawText == wrongGestureMessage:
					braille.handler.message(displayedMessage)
			self.brTimer = Timer(config.conf["braille"]["messageTimeout"], restoreDisplayedMessage)
			self.brTimer.setDaemon(True)
			self.brTimer.start()

	def rectangleFromObject(self, obj, verbose=True):
		if obj:
			if self.rectangle.object: self.oldRectangles.push(self.rectangle)
			self.rectangle = Rectangle().fromObject(obj)
			# Translators: Messages that will be presented when the events occur.
			self.rectangle.bind(EVT_object, evtMessage, _("Reference object has changed"))
			self.rectangle.bind(EVT_objectInside, evtMessage, _("The reference object is fully inside the rectangle"))
			self.rectangle.bind(EVT_objectOverflow, evtMessage, _("The reference object exceeds the bounds of the rectangle"))
			self.rectangle.bind(EVT_overflowWindow, evtMessage, _("The rectangle has overflowed the active window"))
			self.rectangle.bind(EVT_insideWindow, evtMessage, _("The rectangle is inside the active window"))
			if verbose:
				# Translators: Message when an object is framed.
				ui.message(_("Frammed {object} {name} ").format(
				object=controlTypes.role._roleLabels[obj.role], name=obj.name if obj.name and obj.role == controlTypes.Role.WINDOW else ""))
				self.script_rectangleInfo(None)
		else:
			beep(100,50)
			# Translators: Message presented when trying to frame an object but there is none.
			ui.message(_("object not found"))

	def increaseOrDecreaseStep(self, x):
		step = int(config.conf.profiles[0]["screenshots"]["step"])
		step = step+x
		if step < 11 and step > 0:
			config.conf.profiles[0]["screenshots"]["step"] = step
			# Translators: Message   when modifying the amount of movement in pixels
			# Translators: Message presented when the number of pixels per movement is modified.
			ui.message(_("{step} px").format(step=config.conf.profiles[0]["screenshots"]["step"]))
		else:
			self.script_wrongGesture(None)

	def scaleImage(self, img):
		fg = api.getDesktopObject()
		wFactor = fg.location.width/img.Width
		hFactor = fg.location.height/img.Height
		factor = wFactor if wFactor<hFactor else hFactor
		if factor>4: factor = 4 # Enlarging more than 4x produces blurry images.
		return img.Scale(img.Width*factor, img.Height*factor, wx.IMAGE_QUALITY_HIGH)

	__gestures = {
	"kb:printScreen": "keyboardLayer"
	}

	__keyboardLayerGestures = {
	"kb:upArrow": "levelUp",
	"kb:downArrow": "goBack",
	"kb:w": "frameObject",
	"kb:s": "frameObject",
	"kb:f": "frameObject",
	"kb:n": "frameObject",
	"kb:m": "frameObject",
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
	"kb:shift+enter": "saveScreenshot",
	"kb:numpadEnter": "saveScreenshot",
	"kb:shift+rightArrow": "shrinkLeft",
	"kb:shift+leftArrow": "expandLeftward",
	"kb:shift+upArrow": "expandUpward",
	"kb:shift+downArrow": "shrinkAbove",
	"kb:control+rightArrow": "expandRightward",
	"kb:control+leftArrow": "shrinkRight",
	"kb:control+upArrow": "shrinkBottom",
	"kb:control+downArrow": "expandBottomward",
	"kb:control+shift+upArrow": "expandRectangle",
	"kb:control+shift+downArrow": "shrinkRectangle",
	"kb:backspace": "adjustToObject",
	"kb:F1": "help",
	"kb:r": "OCR"
	}

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
