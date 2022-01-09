#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
GUI for screenshots wizard NVDA addon

This file is covered by the GNU General Public License.
Copyright (C) Javi Dominguez 2021
"""

from gui import guiHelper, NVDASettingsDialog
from gui.settingsDialogs import SettingsPanel
import addonHandler
import config
import wx

addonHandler.initTranslation()

class ScreenshotsPanel(SettingsPanel):
	# TRANSLATORS: title for the Update Channel settings category
	title = _("Screenshots Wizard")

	def makeSettings(self, sizer):
		helper = guiHelper.BoxSizerHelper(self, sizer=sizer)

		# Selecting the folder where the image file will be saved
		label = wx.StaticText(self, wx.ID_ANY, _("Select the folder where the image files of the screenshots will be saved"))
		helper.addItem(label)
		sizerDir = wx.BoxSizer(wx.HORIZONTAL)
		self.textPath = wx.TextCtrl (self, style=wx.TE_RICH|wx.TE_NO_VSCROLL|wx.TE_WORDWRAP|wx.TE_MULTILINE|wx.TE_READONLY, value =config.conf.profiles[0]["screenshots"]["folder"],  size=(300,20))
		sizerDir.Add(self.textPath)
		self.buttonBrowse = wx.Button(self, wx.ID_ANY, _("browse"))
		sizerDir.Add(self.buttonBrowse)
		helper.addItem(sizerDir)
		self.buttonBrowse.Bind(wx.EVT_BUTTON, self.onBrowse)

		#  Selecting the format of the image to be saved
		fileFormats = ["BMP", "JPG", "GIF", "PNG", "TIFF"]
		self.radioBoxFormat = wx.RadioBox(self, wx.ID_ANY, _("File format"), choices=fileFormats, majorDimension=5, style=wx.RA_SPECIFY_COLS)
		self.radioBoxFormat.SetSelection(fileFormats.index(config.conf.profiles[0]["screenshots"]["format"]))
		helper.addItem(self.radioBoxFormat)

		# Select what to do after saving the file
		self.radioBoxAction = wx.RadioBox(self, wx.ID_ANY, _("After saving the screenshot"), choices=[_("Nothing"), _("Open file"), _("Open folder")], majorDimension=3, style=wx.RA_SPECIFY_COLS)
		self.radioBoxAction.SetSelection(int(config.conf.profiles[0]["screenshots"]["action"]))
		helper.addItem(self.radioBoxAction)

		# Selecting the number of pixels per step when the rectangle coordinates are modified.
		sizerStep = wx.BoxSizer(wx.HORIZONTAL)
		labelStep = wx.StaticText(self, wx.ID_ANY, _("Movement unit (in pixels): "))
		sizerStep.Add(labelStep)
		self.spin_ctrl = wx.SpinCtrl(self, wx.ID_ANY, str(config.conf.profiles[0]["screenshots"]["step"]), min=1, max=10)
		sizerStep.Add(self.spin_ctrl)
		helper.addItem(sizerStep)

	def onBrowse(self, evt):
		dlg = wx.DirDialog(self, _("Choose a directory:"), style=wx.DD_DEFAULT_STYLE)
		if dlg.ShowModal() == wx.ID_OK:
			self.textPath.SetValue(dlg.GetPath())
			self.textPath.SetFocus()
			dlg.Destroy()

	def onSave(self):
		config.conf.profiles[-1].name = self.originalProfileName
		config.conf.profiles[0]["screenshots"]["folder"] = self.textPath.GetValue()
		config.conf.profiles[0]["screenshots"]["format"] = self.radioBoxFormat.GetStringSelection()
		config.conf.profiles[0]["screenshots"]["action"] = int(self.radioBoxAction.GetSelection())
		config.conf.profiles[0]["screenshots"]["step"] = self.spin_ctrl.GetValue()

	def onDiscard(self):
		config.conf.profiles[-1].name = self.originalProfileName

	def onPanelActivated(self):
		self.originalProfileName = config.conf.profiles[-1].name
		config.conf.profiles[-1].name = None
		self.Show()

	def onPanelDeactivated(self):
		config.conf.profiles[-1].name = self.originalProfileName
		self.Hide()
