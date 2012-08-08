#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
###
# Application: wah!cade
# File:        win_playerSelect.py
# Description: Window that displays a ScrollList containing scores for players to chose from
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
from scrolled_list import ScrollList
from constants import *
from wc_common import WahCade
_ = gettext.gettext

class WinPlayerSelect(WahCade):
    """Window allowing the user to identify themself"""

    def __init__(self, WinMain):
        # Set main window
        self.WinMain = WinMain
        # Build the window
        self.winPlayers = gtk.Fixed()
        self.winPlayers.set_has_window(True)
        self.imgBackground = gtk.Image()
        self.lblScore = gtk.Label()
        self.lbl1 = gtk.Label()
        self.sclPlayers = ScrollList(self.WinMain)
        self.winPlayers.add(self.imgBackground)
        self.winPlayers.add(self.lblScore)
        self.winPlayers.add(self.lbl1)
#        self.winPlayers.add(self.lblRFID)
        self.winPlayers.add(self.sclPlayers.fixd)
        WinMain.fixd.add(self.winPlayers)
        self.imgBackground.show()
        self.lbl1.show()
        self.winPlayers.show()
        # Build list
        self.lsPlayers = self.WinMain.current_players
        self.sclPlayers.auto_update = True
        # Get keyboard & mouse events
        self.sclPlayers.connect('update', self.on_sclPlayers_changed)
        self.sclPlayers.connect('mouse-left-click', self.on_sclPlayers_changed)
        self.sclPlayers.connect('mouse-double-click', self.player_selected)
        # Set up IDs
        self.sclPlayers.ls = [l for l in self.lsPlayers]
        self.sclPlayers.ls.sort()        
        # Init window
        self.lblScore.set_text("Who's score was this?")
        self.lbl1.set_text("-------------")
        self.record = False
        self.on_keypress = False
        
    def populate_list(self):
        self.sclPlayers.ls = [l for l in self.WinMain.current_players]
        self.sclPlayers.ls.sort()
        
        
    def on_sclPlayers_changed(self, *args):
        """Selected user identity changed"""
        # Update list widget
        self.sclPlayers._update_display()
        return
    
    def player_selected(self, *args):
        """ID selected"""
        return
        
        
        
        
        