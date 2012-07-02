# -*- coding: utf-8 -*-
#
###
# Application: Rcade
# File:        scroll_overlay.py
# Description: Transparent/Opaque Indicator For Use With Scrolling List
# Copyright (c) 2012  John Kelly <john.kelly@readytalk.com>
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
#
import sys

#gtk
import pygtk
if sys.platform != 'win32':
    pygtk.require('2.0')
import gtk
from gtk import gdk
import gobject
gobject.threads_init()
import pango

class ScrollOverlay(object):
    """custom scrolling list indicator box"""
    """intended to operate similarly to a gtk.widget"""
    
    def __init__(self, childLabel, childImage):
        """create object"""
        self.lblOverlay = childLabel
        self.lblImage = childImage
        self.lblBG = gtk.EventBox()
        self.data = {}
        
    def show(self):
        self.lblOverlay.show()
        self.lblImage.show()
        self.lblBG.show()
        
    def hide(self):
        self.lblOverlay.hide()
        self.lblImage.hide()
        self.lblBG.hide()
        
    def set_markup(self, markup):
        self.lblOverlay.set_markup(markup)
        
    def modify_bg(self, state, color):
        self.lblBG.modify_bg(state, color)
        
    def modify_fg(self, state, color):
        self.lblBG.modify_fg(state, color)
        
    def set_from_file(self, imgPath):
        self.lblImage.set_from_file(imgPath)
        
    def modify_font(self, fontData):
        self.lblOverlay.modify_font(fontData)
        
    def set_angle(self, angle):
        self.lblOverlay.set_angle(angle)
        
    def set_size_request(self, w, h):
        self.lblImage.set_size_request(w, h)
        self.lblOverlay.set_size_request(w, h)
        
    def get_parent(self):
        return self
    
    def get_ancestor(self, type):
        return None
    
    def set_property(self, key, value):
        if key is 'xalign':
            self.lblOverlay.set_property(key, value)
        else:
            print "scroll overlay tried to set prop " + key
        
    def set_data(self, key, value):
        self.data[key] = value
        
    def add_to_fixd(self, fixd):
        fixd.add(self.lblImage)
        fixd.add(self.lblOverlay)
        
    def move_in_fixd(self, fixd, x, y):
        self.add_to_fixd(fixd)
        fixd.move(self.lblImage,   x, y)
        fixd.move(self.lblOverlay, x, y)