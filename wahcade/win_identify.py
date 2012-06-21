#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
###
# Application: wah!cade
# File:        win_identify.py
# Description: Window that displays a ScrollList containing names for the player to choose from
###
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import sys

# GTK
import pygtk
if sys.platform != 'win32':
    pygtk.require('2.0')
import gtk

# Project modules
from load_LDAP import LoadLDAP
from scrolled_list import ScrollList
from constants import *
from wc_common import WahCade
_ = gettext.gettext

class WinIdentify(WahCade):
    """Window allowing the user to identify themself"""

    def __init__(self, WinMain):
        # Set main window
        self.WinMain = WinMain
        # Build the window
        self.winID = gtk.Fixed()
        self.winID.set_has_window(True)
        self.imgBackground = gtk.Image()
        self.lblPrompt = gtk.Label()
        self.lblPromptText = gtk.Label()
        self.sclIDs = ScrollList()
        self.winID.add(self.imgBackground)
        self.winID.add(self.lblPrompt)
        self.winID.add(self.lblPromptText)
        self.winID.add(self.sclIDs.fixd)
        WinMain.fixd.add(self.winID)
        self.imgBackground.show()
        self.lblPrompt.show()
        self.lblPromptText.show()
        self.winID.show()
        # Build list
        self.ldap = LoadLDAP()
        self.lsIDs = self.ldap.getNames()
#        print self.lsIDs
#        print len(self.lsIDs)
        self.sclIDs.auto_update = True
        self.sclIDs.display_limiters = self.WinMain.wahcade_ini.getint('show_list_arrows', 0)
        # Get keyboard & mouse events
        self.sclIDs.connect('update', self.on_sclIDs_changed)
        self.sclIDs.connect('mouse-left-click', self.on_sclIDs_changed)
        self.sclIDs.connect('mouse-double-click', self.ID_selected)
        # Set up IDs
        self.sclIDs.ls = [l for l in self.lsIDs]
        self.sclIDs.ls.sort()
        #print self.sclIDs.ls
        
        ## TODO: Exclude IDs already matched to RFID values
        
        # Init window
        self.sclIDs.use_mouse = self.WinMain.ctrlr_ini.getint('mouse')
        self.sclIDs.wrap_list = self.WinMain.wahcade_ini.getint('wrap_list')
        self.record = False
        self.on_keypress = False        
        
    def on_sclIDs_changed(self, *args):
        """Selected user identity changed"""
        # Update list widget
        self.sclIDs._update_display()
        #print self.sclIDs.ls[self.sclIDs.get_selected()]
        return
    
    def ID_selected(self, *args):
        """ID selected"""
        return
    
    ## TODO: Add ability to jump alphabetically
        
        
        
        
        


