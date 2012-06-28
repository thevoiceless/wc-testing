#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
###
# Application: wah!cade
# File:        win_popular.py
# Description: Window that displays a ScrollList containing poopular games for the user to choose from
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

# Sys
import sys
# Wahcade
from scrolled_list import ScrollList
from wc_common import WahCade
# GTK
import pygtk
if sys.platform != 'win32':
    pygtk.require('2.0')
import gtk

class WinPopular(WahCade):
    """Window allowing user to select a popular game"""
    
    def __init__(self, WinMain):
        # Main parent window
        self.WinMain = WinMain
        # Internals
        self.winPop = gtk.Fixed()
        self.winPop.set_has_window(True)
        self.imgBackground = gtk.Image()
        self.lblHeading = gtk.Label()
        self.sclPop = ScrollList(self.WinMain)
        self.winPop.add(self.imgBackground)
        self.winPop.add(self.lblHeading)
        self.winPop.add(self.sclPop.fixd)
        WinMain.fixd.add(self.winPop)
        self.imgBackground.show()
        self.lblHeading.show()
        self.sclPop.show()
        # Get keyboard & mouse events
        self.sclPop.connect('update', self.on_sclPop_changed)
        self.sclPop.connect('mouse-left-click', self.on_sclPop_changed)
        self.sclPop.connect('mouse-double-click', self.Pop_selected)
        # Set up games list
        self.sclPop.auto_update = True
        self.lsPop = ["Game", "Other Game", "Best Game", "#4", "#5", "#6", "#7", "#8", "#9", "#10"]
        self.sclPop.ls = [g for g in self.lsPop]
        self.sclPop.ls.sort()
        self.sclPop._update_display()
        # Set text
        self.lblHeading.set_text("10 Most Popular Games")
        
    def on_sclPop_changed(self, *args):
        """List is scrolling somehow"""
        # Update the display
        self.sclPop._update_display()
        pass
    
    def Pop_selected(self):
        pass
    
    def set_games_list(self, games):
        self.lsPop = games
        self.sclPop.ls = [g for g in games]
        self.sclPop._update_display