#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
###
# Application: wah!cade
# File:        wahcade
# Description: starts the wah!cade app
# Copyright (c) 2005-2010   Andy Balcombe <http://www.anti-particle.com>
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
assert(sys.version_info) >= (2, 4, 0), 'python >= 2.4 required'
from optparse import OptionParser   # http://docs.python.org/library/optparse.html
                                    # Deprecated since version 2.7: The optparse module is deprecated and will not be developed further; development will continue with the argparse module.

from constants import *             # constants.py, http://docs.python.org/library/constants.html

import exception                    # exception.py, http://docs.python.org/library/exceptions.html
_ = gettext.gettext                 # _ now does the same thing as using gettext.gettext("message")

if __name__ == "__main__":          # http://stackoverflow.com/questions/419163/what-does-if-name-main-do
    #set to unicode encoding
    try:
        sys.setappdefaultencoding('utf-8')
    except AttributeError:
        pass
    #define options
    parser = OptionParser(version='%s %s "%s"' % ("%prog", VERSION, VERSION_NAME))
    parser.add_option("-w", "--window",
                        action="store_true",
                        dest="windowed",
                        default=False,
                        help=_('Set windowed mode'))
    parser.add_option("-f", "--full-screen",
                        action="store_true",
                        dest="fullscreen",
                        default=False,
                        help=_('Set fullscreen mode'))
    parser.add_option("-d", "--debug",
                        action="store_true",
                        dest="debug",
                        default=False,
                        help=_('Set debug mode (disables psyco)'))
    parser.add_option("--no-gstreamer",
                        action="store_true",
                        dest="disable_gstreamer",
                        default=False,
                        help=_('Set to disable all gstreamer use (music / video playback)'))
    parser.add_option("--no-pygame",
                        action="store_true",
                        dest="disable_pygame",
                        default=False,
                        help=_('Set to disable all pygame use (joysticks)'))
    parser.add_option("--old-key-handler",
                        action="store_true",
                        dest="old_keyb_events",
                        default=False,
                        help=_('Set to revert to old keyboard event handling'))
    #get options & arguments
    # parse_args() returns two values:
    #    1. options, an object containing values for all of your options—e.g. if --file takes a single string argument, then options.file will be the filename supplied by the user, or None if the user did not supply that option
    #    2. args, the list of positional arguments leftover after parsing options
    options, args = parser.parse_args()
    #debug mode set?
    if not options.debug:
        #import psyco if available
        try:
            import psyco            # http://psyco.sourceforge.net/, "Psyco is unmaintained and dead. Please look at PyPy for the state-of-the-art in JIT compilers for Python."
            psyco.full()
        except ImportError:
            pass
        #set exception handler to gtk2 handler
        sys.excepthook = exception._info
    #instantiate main GUI window class
    #do this here as it stops weird gstreamer messages
    from win_main import WinMain, gtk   # Imports WinMain and gtk from win_main.py
    app = WinMain(options)              # class WinMain(WahCade)
    #and... go...
    gtk.main()