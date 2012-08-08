# -*- coding: utf-8 -*-
#
###
# Application: Rcade
# File:        wahcade.py
# Description: Main Window
# Created by Andy Balcombe. Extended by Zach McGaughey, Riley Moses, Devin Wilson, John Kelly and Terek Campbell of ReadyTalk
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

## System Modules
import sys
import glob
import random
import time
import gc
import re
import imp
import shlex
import os
import commands
from operator import itemgetter
import subprocess
from subprocess import Popen
import yaml #@UnresolvedImport
import serial
import Queue
import codecs

## GTK Modules
# GTK
import pygtk                        # http://www.pygtk.org/
from random import Random
onWindows = True
if not sys.platform.startswith('win'):
    pygtk.require('2.0')            # Require GTKv2 (standard, as GTKv3 is still new)
    onWindows = False
import gtk
import gobject                      # https://live.gnome.org/PyGObject
gobject.threads_init()              # Initializes the the use of Python threading in the gobject module
import pango                        # Library for rendering internationalized texts in high quality, http://zetcode.com/tutorials/pygtktutorial/pango/

# Get system path separator
sep = os.sep

# dbus
dbus_imported = False
try:
    import dbus                     # Messaging library used by various desktop environments for interprocess communication, http://dbus.freedesktop.org/doc/dbus-python/doc/tutorial.html
    dbus_imported = True
except ImportError:
    pass

# gStreamer Modules
gst_media_imported = False
try:
    import gst_media                # /usr/share/games/wahcade/gst_media.py
    gst_media_imported = True
except:
    pass

### Project modules
from constants import *
from scrolled_list import ScrollList    # Transparent scrolled list widget
from scroll_overlay import ScrollOverlay# Custom overlay text/image container
from key_consts import mamewah_keys     # Keyboard constants
from wc_common import WahCade           # Common functions for wahcade
from win_options import WinOptions      # Options window
from win_message import WinMessage      # Message window
from win_scrsaver import WinScrSaver    # Screen saver window
from win_history import WinHistory      # History viewer
from win_cpviewer import WinCPViewer    # Control panel viewer window
from win_identify import WinIdentify    # Identify window
from win_playerSelect import WinPlayerSelect #Player selection window
import threading
import filters                          # filters.py, routines to read/write mamewah filters and lists
from mamewah_ini import MameWahIni      # Reads mamewah-formatted ini file
import joystick                         # joystick.py, joystick class, uses pygame package (SDL bindings for games in Python)
import requests
import pygame
from video_chat import video_chat       #import the video chat element
from xml.etree.ElementTree import fromstring
# Set gettext function
_ = gettext.gettext

class WinMain(WahCade, threading.Thread):
    """Rcade Main Window"""          # This is the docstring belonging to the class, __doc__

    def __init__(self, config_opts):
        """Initialize main Rcade window"""   # Docstring for this method

        ### Set Global Variables
        global gst_media_imported, pygame_imported, old_keyb_events, debug_mode, log_filename
        self.init = True
        WahCade.__init__(self)
        
        ### Defaults
        pygame_imported = True
        old_keyb_events = False
        debug_mode = False
        self.remote_ip = None
        self.video_chat_enabled = False
        self.showOverlayThresh = 10
        self.showImgThresh = 6
        self.showHighScoreThresh = 10
        self.listIndex = 0
        self.scroll_count = 0
        self.chat_key_count = 0
        
        ### USER PROFILE
        self.userpath = os.path.expanduser(CONFIG_DIR)  # CONFIG_DIR comes from constants.py
        if not os.path.exists(CONFIG_DIR):
            # Copy over ALL config files
            self.copy_user_config('all')                # copy_user_config comes from wc_common.py
            # Now we've copied stuff, quit and tell the user
            self.log_msg("First run, Wah!Cade setting user config profile in: "+ self.userpath,0)   # log_msg comes from wc_common.py
            self.log_msg("Restart after configuring (run wahcade-setup or see the README file).",0)
            sys.exit(0)
        else:
            # Update current config
            self.copy_user_config()
            # Now we've copied stuff, quit and tell the user
            self.log_msg("Wah!Cade updating user config files in: "+ self.userpath)
            
        keyfile = CONFIG_DIR + "/confs/authkeys"
        try:
            with open(keyfile, 'r') as f:
                key = f.readline().strip()             
        except:
            self.authorization = {"Authorization" : "Basic " + "user:pass".encode('base64', 'strict').strip()}
        else:
            self.authorization = {"Authorization" : "Basic " + key.encode('base64', 'strict').strip()}
        # Try connecting to a database, otherwise
        self.db_file = CONFIG_DIR + "/confs/DB-" + config_opts.db_config_file + ".txt"
        try:
            with open(self.db_file, 'rt') as f: # Open the config file and extract the database connection information
                self.props = {}  # Dictionary
                for line in f.readlines():
                    val = line.split('=')
                    self.props[val[0].strip()] = val[1].strip()  # Match each key with its value
                r = requests.get(self.props['host'] + ":" + self.props['port'] + "/" + self.props['db']) # Attempt to make connection to server
                self.check_connection(r.status_code)
        except requests.exceptions.ConnectionError, e: # Any exception would mean some sort of failed server connection
            self.connected_to_server = False
            print "Failed to connect to", self.props['host'] + ":" + self.props['port'] + "/" + self.props['db'] + ":", str(e)
        if self.connected_to_server:
            print "Successfully connected to the server:", self.props['host'] + ":" + self.props['port'] + "/" + self.props['db']
        ### SETUP WAHCADE INI FILE
        self.wahcade_ini = MameWahIni(os.path.join(CONFIG_DIR, 'wahcade.ini'))
        ## Read in options wahcade.ini, 
        self.lck_time = self.wahcade_ini.getint('lock_time')        # getint comes from mamewah_ini.py
        self.keep_aspect = self.wahcade_ini.getint('keep_image_aspect')
        self.scrsave_delay = self.wahcade_ini.getint('delay')
        self.auto_logout_delay = self.wahcade_ini.getint('log_out')
        self.hide_log_delay = self.wahcade_ini.getint('hide_message')
        self.layout_orientation = self.wahcade_ini.getint('layout_orientation', 0)
        self.screentype = self.wahcade_ini.getint('fullscreen', 0)
        self.intro_movie = self.wahcade_ini.get('intro_movie_file')
        self.showcursor = self.wahcade_ini.getint('show_cursor')       
        self.display_limiters = self.wahcade_ini.getint('show_list_arrows', 0)
        self.wrap_list = self.wahcade_ini.getint('wrap_list')
        self.movievol = self.wahcade_ini.getint('movie_volume')
        self.music_enabled = self.wahcade_ini.getint('enable_music')
        self.music_vol = self.wahcade_ini.getint('music_volume')
        self.musicpath = self.wahcade_ini.get('music_path')
        self.musicshuffle = self.wahcade_ini.get('shuffle_music', 0)
        self.music_movies_mix = self.wahcade_ini.get('music_movie_mix')
        self.sound_vol = self.wahcade_ini.getint('sound_volume')
        self.sound_enabled = self.wahcade_ini.getint('enable_sounds')
        self.delaymovieprev = self.wahcade_ini.getint('delay_before_movie_preview')
        self.exit_movie_file = self.wahcade_ini.get('exit_movie_file') 
        self.layout = self.wahcade_ini.get('layout')
        self.use_splash = self.wahcade_ini.getint('use_splash',1)
        self.splash_show_text = self.wahcade_ini.getint('splash_show_text',1)
        self.splash_border_width = self.wahcade_ini.getint('splash_border_width',10)
        
        ### SETUP EMULATOR INI FILE       
        self.current_emu = self.wahcade_ini.get('current_emulator')
        self.emu_ini = MameWahIni(os.path.join(CONFIG_DIR, 'ini' + sep + self.current_emu + '.ini'))
        ## read in options emulator.ini,        
        self.emumovieprevpath = self.emu_ini.get('movie_preview_path')
        self.emumovieartworkno = self.emu_ini.getint('movie_artwork_no')

        ### SETUP CTRLR INI
        self.ctrlr_ini = MameWahIni(os.path.join(CONFIG_DIR, 'ctrlr', 'default.ini'), 'ctrlr')
        self.use_mouse = self.ctrlr_ini.getint('mouse')
        self.joyint = self.ctrlr_ini.getint('joystick')
        self.dx_sensitivity = self.ctrlr_ini.getint('mouse_x_sensitivity',100) * 0.01
        self.dy_sensitivity = self.ctrlr_ini.getint('mouse_y_sensitivity',100) * 0.01
        
        ### SET CABINET NAME
        self.cabinet_name = self.ctrlr_ini.get('cabinet_name')

        ### Command-line options (parsed after ini is read)
        self.check_params(config_opts)

        ### LOCK FILE
        self.lock_filename = os.path.join(CONFIG_DIR, 'emulator.lck')
        ### remove lock file if it exists
        if os.path.exists(self.lock_filename):
            self.log_msg('Lock file found: Removing')
            os.remove(self.lock_filename)
            if not os.path.exists(self.lock_filename):
                self.log_msg('Lock File removed successfully')

        ### WINDOW SETUP            
        # Build the main window
        self.winMain = gtk.Window()                 # http://www.pygtk.org/docs/pygtk/class-gtkwindow.html
        self.fixd = gtk.Fixed()                     # http://www.pygtk.org/docs/pygtk/class-gtkfixed.html
        self.imgBackground = gtk.Image()            # http://www.pygtk.org/docs/pygtk/class-gtkimage.html
        self.imgMainLogo = gtk.Image()
        self.lblGameListIndicator = gtk.Label()     # http://www.pygtk.org/docs/pygtk/class-gtklabel.html
        self.lblEmulatorName = gtk.Label()
        self.lblGameSelected = gtk.Label()
        
        if self.cabinet_name == "":
            self.ctrlr_ini.set('cabinet_name', self.set_name_dialog())
            self.ctrlr_ini.write()
        
        if self.use_splash == 1:
            self.display_splash() 
        if gst_media_imported:
            self.drwVideo = gst_media.VideoWidget()
        else:
            self.drwVideo = gtk.Image()
        self.imgArtwork1 = gtk.Image()
        self.imgArtwork2 = gtk.Image()
        self.imgArtwork3 = gtk.Image()
        self.imgArtwork4 = gtk.Image()
        self.imgArtwork5 = gtk.Image()
        self.imgArtwork6 = gtk.Image()
        self.imgArtwork7 = gtk.Image()
        self.imgArtwork8 = gtk.Image()
        self.imgArtwork9 = gtk.Image()
        self.imgArtwork10 = gtk.Image()
        self.lblGameDescription = gtk.Label()
        self.lblRomName = gtk.Label()
        self.lblYearManufacturer = gtk.Label()
        self.lblScreenType = gtk.Label()
        self.lblControllerType = gtk.Label()
        self.lblDriverStatus = gtk.Label()
        self.lblCatVer = gtk.Label()
        self.lblHighScoreData = gtk.Label()
        self.lblUsers = gtk.Label()
        self.lblUsersLoggedIn = gtk.Label()
        self.lblUsersLoggedOut = gtk.Label()
        # Overlay for games list
        self.gamesOverlayBG = gtk.Image()
        self.lblGamesOverlayScrollLetters = gtk.Label()
        self.gamesScrollOverlay = ScrollOverlay(self.lblGamesOverlayScrollLetters, self.gamesOverlayBG)
        # Overlay for IDs list
        self.IDsOverlayBG = gtk.Image()
        self.lblIDsOverlayScrollLetters = gtk.Label()
        self.IDsScrollOverlay = ScrollOverlay(self.lblIDsOverlayScrollLetters, self.IDsOverlayBG)


        # Create scroll list widget
        self.scroll_selected_color = '#C5C5C5' # Default in case layout doesn't load
        self.selected_player = ''
        self.sclGames = ScrollList(self) 
        self._main_images = [
            self.imgArtwork1,
            self.imgArtwork2,
            self.imgArtwork3,
            self.imgArtwork4,
            self.imgArtwork5,
            self.imgArtwork6,
            self.imgArtwork7,
            self.imgArtwork8,
            self.imgArtwork9,
            self.imgArtwork10]
        self.visible_img_list = []
        self.visible_img_paths = []
        self._main_labels = [
            # self.lblGameListIndicator,
            self.lblGameSelected,
            self.lblGameDescription,
            self.lblRomName,
            self.lblYearManufacturer,
            self.lblScreenType,
            self.lblControllerType,
            self.lblDriverStatus,
            self.lblCatVer] 
        # Add widgets to main window
        self.current_window = 'main'
        self.fixd.add(self.imgBackground)
        self.imgBackground.show()
        
        # Mark mame directory for HiToText calls
        self.mame_dir = os.path.expanduser('~/.mame/')
        # Give absolute path to HiToText using mono
        # Set initial HiToText "read" command
        self.htt_read = "/usr/local/bin/HiToText.exe -r " + self.mame_dir
        # Set initial HiToText "erase" command
        self.htt_erase = "/usr/local/bin/HiToText.exe -e " + self.mame_dir
        
        self.launched_game = False
        self.current_rom = ''
               
        # Video widget
        self.video_playing = False
        self.video_enabled = False
        self.video_timer = None
        self.video_player = None
        self.drwVideo.show()
        self.fixd.add(self.drwVideo)
        
        # Load list of games supported by HiToText
        self.supported_games = []
        self.supported_games_name = []
        self.supported_game_file = open('supported_games.lst')
        for line in self.supported_game_file:
            self.supported_games.append(line.strip())

        # List
        self.sclGames.auto_update = False
        self.sclGames.display_limiters = self.display_limiters
        # Set window properties
        self.winMain.set_position(gtk.WIN_POS_NONE)
        self.winMain.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_NORMAL)
        self.winMain.set_title('Rcade')
        # Init random engine
        random.seed()
        # Build list
        self.current_players = []
        self.score_processing_queue = []
        self.upload_queue = []
        self.lsGames = []
        self.lsGames_len = len(self.lsGames)
        # Timers
        self.scrsave_time = time.time()
        self.portal_time_last_played = time.time()
        self.portal_time = None
        self.timeLogoutShown = time.time()
        self.timeLoginShown = time.time()
       
        ### Create options window
        self.options = WinOptions(self)
        self.options.winOptions.hide()
        ### Create message window
        self.message = WinMessage(self)
        self.message.winMessage.hide()
        ### Create screen saver window
        self.scrsaver = WinScrSaver(self)
        self.scrsaver.winScrSaver.hide()
        self.scrsave_timer = None
        ### Create history viewer window
        self.cpviewer = None
        self.histview = WinHistory(self)
        ### Create CP viewer window
        self.cpviewer = WinCPViewer(self)
        ### Create identify window
        self.identify = WinIdentify(self)
        self.identify.winID.hide()
        ### Create player select window
        self.player_select = WinPlayerSelect(self)
        self.player_select.winPlayers.hide()
        
        self.hide_window()
        
        ### Build list of emulators
        self.emu_lists = self.buildemulist()            # wc_common.py
        
        ### Check that current emu exists...
        el = [e[1] for e in self.emu_lists]
        if self.current_emu not in el:
            #...no, switch to one that does
            self.current_emu = el[0]
            self.wahcade_ini.set('current_emulator', self.current_emu)  # mamewah_ini.py
        
        # Collect all image & label lists
        self._main_items = [
            (self.imgMainLogo, "MainLogo"),                          # Weird gray area at top of window
            (self.lblGameListIndicator, "GameListIndicator"),       # Label above games list
            (self.lblEmulatorName, "EmulatorName"),                 # Label above artwork
            (self.lblGameSelected, "GameSelected"),                 # Label displaying selected game number out of the total
            (self.imgArtwork1, "MainArtwork1"),                     # Large game image in top right
            (self.imgArtwork2, "MainArtwork2"),                     # Smaller game image in the lower right
            (self.imgArtwork3, "MainArtwork3"),                     # Large game image in top center
            (self.imgArtwork4, "MainArtwork4"),                    # Large game image in top center
            (self.imgArtwork5, "MainArtwork5"),                    # Large game image in top center
            (self.imgArtwork6, "MainArtwork6"),                    # Large game image in top center with background
            (self.imgArtwork7, "MainArtwork7"),                    # Large game image in top center
            (self.imgArtwork8, "MainArtwork8"),                    # Large game image in top center
            (self.imgArtwork9, "MainArtwork9"),                    # Large game image in top center
            (self.imgArtwork10, "MainArtwork10"),                  # Large game image in top center
            (self.sclGames, "GameList"),                            # Game list
            (self.lblGameDescription, "GameDescription"),          # Which game is selected
            (self.lblRomName, "RomName"),                          # Rom name
            (self.lblYearManufacturer, "YearManufacturer"),        # Year
            (self.lblScreenType, "ScreenType"),                    # Screen
            (self.lblControllerType, "ControllerType"),            # Controller
            (self.lblDriverStatus, "DriverStatus"),                # Driver
            (self.lblCatVer, "CatVer"),
            (self.gamesScrollOverlay, "ScrollOverlay"),
            (self.lblHighScoreData, "HighScoreData"),               # High score data
            (self.lblUsers, "Users"),                               # Currently logged in users
            (self.lblUsersLoggedIn, "UsersLoggedIn"),               # Show when user(s) log in
            (self.lblUsersLoggedOut, "UsersLoggedOut")]             # Show when user(s) log out
        self._options_items = [
            (self.options.lblHeading, "OptHeading"),               # Options window title
            (self.options.sclOptions, "OptionsList"),              # Options list
            (self.options.lblSettingHeading, "SettingHeading"),    # "Current setting"
            (self.options.lblSettingValue, "SettingValue")]        # Value of current setting
        self._message_items = [      
            (self.message.lblHeading, "MsgHeading"),               # Message window title
            (self.message.lblMessage, "Message"),                  # Message displayed in message window
            (self.message.lblPrompt, "Prompt")]
        self._screensaver_items = [              
            (self.scrsaver.imgArtwork1, "ScrArtwork1"),
            (self.scrsaver.imgArtwork2, "ScrArtwork2"),
            (self.scrsaver.imgArtwork3, "ScrArtwork3"),
            (self.scrsaver.imgArtwork4, "ScrArtwork4"),
            (self.scrsaver.imgArtwork5, "ScrArtwork5"),
            (self.scrsaver.imgArtwork6, "ScrArtwork6"),
            (self.scrsaver.imgArtwork7, "ScrArtwork7"),
            (self.scrsaver.imgArtwork8, "ScrArtwork8"),
            (self.scrsaver.imgArtwork9, "ScrArtwork9"),
            (self.scrsaver.imgArtwork10, "ScrArtwork10"),
            (self.scrsaver.lblGameDescription, "GameDescription"),
            (self.scrsaver.lblMP3Name, "MP3Name")]
        self._identify_items = [
            (self.identify.lblPrompt, "Prompt"),
            (self.identify.lblPromptText, "PromptText"),
            (self.identify.lblRFID, "RFID"),
            (self.identify.sclIDs, "IDsList"),
            (self.IDsScrollOverlay, "ScrollOverlay")]
        self._player_select_items = [
            (self.player_select.lblScore, "lblScore"),
            (self.player_select.lbl1, "lbl1"),
            (self.player_select.sclPlayers, "playersList")]
        self._layout_items = {'main': self._main_items,
                              'options': self._options_items,
                              'message': self._message_items,
                              'screensaver': self._screensaver_items,
                              'identify' : self._identify_items,
                              'playerselect' : self._player_select_items}
 
        # Initialize primary Fixd containers, and populate appropriately
        self.winMain.add(self.fixd)
        # Add everything to the main Fixd object
        for w_set_name in self._layout_items:
            for widget, name in self._layout_items[w_set_name]: #@UnusedVariable
                if widget.get_parent():
                    pass
                elif not (type(widget) is ScrollList):
                    self.fixd.add(widget)
                else:
                    self.fixd.add(widget.fixd)
            
        ### Load list
        self.current_list_ini = None
        self.emu_ini = None
        self.layout_file = ''
        self.load_emulator()
                
        # Get a list of games already on the server
        self.game_url = self.props['host'] + ":" + self.props['port'] + "/" + self.props['db'] + "/rest/game/"
        self.player_url = self.props['host'] + ":" + self.props['port'] + "/" + self.props['db'] + "/rest/player/rcade/"
        self.score_url = self.props['host'] + ":" + self.props['port'] + "/" + self.props['db'] + "/rest/score/"
        self.connected_to_arduino = False
        self.nameToRom = {}
        if self.connected_to_server:
            try:
                # Map rom name to associated game name
                romToName = {}
                for sublist in self.lsGames: 
                    romToName[sublist[1]] = sublist[0]
                for game in romToName:
                    if game in self.supported_games:
                        self.supported_games_name.append(romToName[game])
                # Get a list of games already on the server
                r = requests.get(self.game_url, headers=self.authorization, timeout=1)
                if r.status_code == 401:
                    print 'Not authorized to connect to server. Check confs/authkeys for server admin credentials'
                    raise Exception("Not authorized to connect to server")
                data = fromstring(r.text)

                games_on_server = []
                for game in data.getiterator('game'):
                    games_on_server.append(game.find('romName').text)
                # Add games to the server if not on the server
                for rom in self.supported_games:
                    if rom not in games_on_server and rom in romToName:
                        post_data = {"romName":rom, "gameName":romToName[rom]}
                        r = requests.post(self.game_url, post_data)
            except:
                self.connected_to_server = False                    

        # Setup login
        self.player_info = []
        self.unregistered_users = []
        self.recent_log = False
        self.timer_existing = False
        self.main_log = False
        self.not_in_database = True
        self.running = True
        self.last_log = ''
        if self.connected_to_server:
            # List the contents of /dev/serial/by-id and follow the symbolic link to find where the Arduino is mounted
            try:
                if not os.path.isdir("/dev/serial/by-id"):
                    raise RuntimeError("Device not connected")
                output = subprocess.Popen("ls /dev/serial/by-id -l | grep FTDI", stdout=subprocess.PIPE, shell=True).stdout.read()
                # Split the output, only the end is relevant
                result = output.split(' ')
                # The last part of the result is the symbolic link target
                arduino_mount = result[len(result) - 1].strip()
                # Create the final path
                arduino_mount = '/dev' + arduino_mount[arduino_mount.rfind('/'):]
                self.rfid_reader = serial.Serial(arduino_mount, 9600)
                self.connected_to_arduino = True
                print "Successfully connected to Arduino mounted at", arduino_mount
                # Begin the thread for reading from arduino
                threading.Thread.__init__(self)
                self.start()
            except RuntimeError, e:
                self.connected_to_arduino = False
                print "Failed to connect to Arduino:", str(e)
        if self.connected_to_server:
            self.running = True
            if self.connected_to_arduino:
                self.log_in_queue = Queue.Queue()
                # Get players from server
            try:
                data = fromstring(requests.get(self.player_url, headers=self.authorization).text)
            except:
                self.connected_to_server = False
            for player in data.getiterator('player'):
                self.player_info.append((player.find('name').text, player.find('playerID').text)) # parse player name and RFID from xml
            self.lblUsers.set_text("No Users Logged In")
            self.lblUsers.show()
       
        # Generate unregistered user list
        self.identify.Setup_IDs_list()
        pygame.init()
        sound_files = os.listdir(CONFIG_DIR + '/sounds/')
        self.sounds = []
        for sound in sound_files:
            self.sounds.append(CONFIG_DIR + '/sounds/' + sound)

        self.check_music_settings()
        self.winMain.show()
        self.drwVideo.set_property('visible', False)
        
        # Initialize video chat
        self.video_chat = None
        if self.connected_to_server:
            self.connection_url = self.props['host'] + ":" + self.props['port'] + "/" + self.props['db'] + "/rest/connection/rcade/"
            self.video_chat = video_chat(self)
            self.vid_container = gtk.VBox(False, 10)
            self.vc_box = gtk.DrawingArea()
            self.vc_box.modify_bg(gtk.STATE_NORMAL, self.vid_container.style.black)
            self.vc_box.set_size_request(self.video_chat.video_width, self.video_chat.video_height)
            self.vid_container.pack_start(self.vc_box)
            self.vc_caption = gtk.Label("Waiting for another user to join...")
            self.vc_caption.modify_fg(gtk.STATE_NORMAL, self.vc_caption.style.white)
            self.vid_container.pack_start(self.vc_caption)
            self.fixd.put(self.vid_container, 603, 140)
            
            #self.setup_video_chat()
        
        if not self.showcursor:
            self.hide_mouse_cursor(self.winMain)
        self.screen = self.winMain.get_screen()
        self.display = self.screen.get_display()
        self.old_mouse = (0, 0)
        
        # Fullscreen
        if self.screentype == 1:
            self.log_msg('Fullscreen mode')
            self.winMain.fullscreen()
        else:
            self.log_msg('Windowed mode')
        
        # Show the window to the user
        self.winMain.present()
        if self.use_splash == 1:
            ### Hide splash
            self.splash.destroy()
        self.do_events()
        self.on_winMain_focus_in()

        #### Start intro movie
        if gst_media_imported and os.path.isfile(self.intro_movie):
            self.scrsaver.play_movie(
                self.intro_movie,
                'intro')
            self.log_msg("Found intro movie file, attempting to play " + self.intro_movie)
        else:
            self.start_timer('scrsave')
            self.start_timer('portal')
            if gst_media_imported and self.music_enabled:
                self.gstMusic.play()

        ### INPUT CONFIGURATION
        # Input defaults
        self.pointer_grabbed = False
        # Get keyboard and mouse events
        self.sclGames.connect('update', self.on_sclGames_changed)
        self.sclGames.connect('mouse-left-click', self.on_sclGames_changed)
        self.sclGames.connect('mouse-right-click', self.on_winMain_key_press)
        self.sclGames.connect('mouse-double-click', self.launch_auto_apps_then_game)
        self.winMain.connect('destroy', self.on_winMain_destroy)
        self.winMain.connect('focus-in-event', self.on_winMain_focus_in)
        self.winMain.connect('focus-out-event', self.on_winMain_focus_out)
        self.winMain.add_events(
            gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.SCROLL_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK |
            gtk.gdk.KEY_PRESS_MASK |
            gtk.gdk.KEY_RELEASE_MASK)
        key_press_events = [
            'key-press-event', 'key-release-event', 'button-release-event',
            'scroll-event', 'motion-notify-event']
        [self.winMain.connect(kpev, self.on_winMain_key_press) for kpev in key_press_events]
        self.sclGames._update_display()
        #[self.drwVideo.connect(kpev, self.on_winMain_key_press) for kpev in key_press_events]
        #key_press_events = ['key-press-event', 'key-release-event']
        #[self.drwVideo.connect(kpev, self.on_winMain_key_press) for kpev in key_press_events]
        self.main_scroll_keys = [
            'UP_1_GAME', 'DOWN_1_GAME',
            'UP_1_PAGE', 'DOWN_1_PAGE',
            'UP_1_LETTER', 'DOWN_1_LETTER']
        self.scroll_count = 0
        self.fixd.show()
        #### Joystick setup
        self.joy = None
        if (self.joyint == 1) and pygame_imported:
            self.joy = joystick.joystick(debug_mode)
            self.joy.use_ini_controls(self.ctrlr_ini)
            self.joy.joy_info()
            self.start_timer('joystick')
        self.on_sclGames_changed()
        ### __INIT__ Complete
        self.init = False
    
    def responseToDialog(self, entry, dialog, response):
        dialog.response(response)
    
    def set_name_dialog(self):
        #base this on a message dialog
        dialog = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons = gtk.BUTTONS_OK, parent=self.winMain)
        dialog.set_markup('Please enter cabinet <b>name</b>:')
        #create the text input field
        entry = gtk.Entry()
        #allow the user to press enter to do ok
        entry.connect("activate", self.responseToDialog, dialog, gtk.RESPONSE_OK)
        #create a horizontal box to pack the entry and a label
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label("Name:"), False, 5, 5)
        hbox.pack_end(entry)
        #some secondary text
        dialog.format_secondary_markup("Leave blank for 'ReadyTalk'")
        #add it and show it
        dialog.vbox.pack_end(hbox, True, True, 0)
        dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dialog.set_keep_above(True)
        dialog.show_all()

        dialog.run()
        text = entry.get_text().strip()
        if text == "":
            text = "ReadyTalk"
        dialog.destroy()
        return text
    
    def on_winMain_destroy(self, *args):
        """Done, quit the application"""
        # Stop video playing if necessary
        self.stop_video()
        # Stop video streaming
        if self.video_chat and self.video_chat.enabled:
            self.clean_up_video_chat()
        # Tells the arduino thread to terminate properly
        self.current_window = 'main'
        self.running = False
        # Save ini files
        self.wahcade_ini.write()
        self.emu_ini.write()
        self.current_list_ini.write()
        # Write favorites list
        filters.write_fav_list(
            os.path.join(CONFIG_DIR, 'files', '%s.fav' % (self.current_emu)),
            self.emu_favs_list)
        # Exit GTK loop
        gtk.main_quit()
        sys.exit(0)

    def exit_wahcade(self, exit_mode='default'):
        """Quit"""
        exit_movie = os.path.isfile(self.exit_movie_file)
        self.stop_video()
        if dbus_imported:
                bus = dbus.SystemBus()
                try:
                    # CONSOLE KIT
                    ck_obj = bus.get_object('org.freedesktop.ConsoleKit', '/org/freedesktop/ConsoleKit/Manager')
                    ck = dbus.Interface(ck_obj, 'org.freedesktop.ConsoleKit.Manager')
                except:
                    # HAL
                    hal_obj = bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/devices/computer')
                    hal = dbus.Interface(hal_obj, 'org.freedesktop.Hal.Device.SystemPowerManagement')
        if exit_mode == 'default':
            if gst_media_imported and exit_movie:
                # Start exit movie
                self.log_msg('Exit with movie file, exit mode selected')
                self.scrsaver.play_movie(exit_movie,'exit')
            else:
                self.log_msg('Default, exit mode selected')
                self.on_winMain_destroy()
        elif exit_mode == 'reboot':
            # Reboot
            self.log_msg('Reboot, exit mode selected')
            try:
                ck.Restart()
            except: 
                hal.Reboot()
        elif exit_mode == 'shutdown':
            # Turn off
            self.log_msg('Shutdown, exit mode selected')
            try:
                ck.Stop() 
            except:
                hal.Shutdown()
        self.on_winMain_destroy()

    def on_winMain_focus_in(self, *args):
        """Window received focus"""
        self.pointer_grabbed = False
        if self.sclGames.use_mouse and not self.showcursor:
            # Need to grab?
            mw_keys = ['MOUSE_LEFT', 'MOUSE_RIGHT', 'MOUSE_UP', 'MOUSE_DOWN']
            for mw_key in mw_keys:
                mw_functions = self.ctrlr_ini.reverse_get(mw_key)
                if mw_functions:
                    # Grab pointer
                    r = gtk.gdk.pointer_grab(
                        self.winMain.window,
                        event_mask= gtk.gdk.POINTER_MOTION_MASK |
                            gtk.gdk.SCROLL_MASK |
                            gtk.gdk.BUTTON_RELEASE_MASK |
                            gtk.gdk.KEY_PRESS_MASK |
                            gtk.gdk.KEY_RELEASE_MASK)#,
                        #confine_to=self.winMain.window)
                    if r==gtk.gdk.GRAB_SUCCESS:
                        self.pointer_grabbed = True
                    # Done
                    #break
        # Remove Lock File workaround
        self.log_msg("Here", "debug")
        if os.path.exists(self.lock_filename):
            self.log_msg('Lock file found: Waiting ' + str(self.lck_time))
            self.wait_with_events(self.lck_time)
            self.log_msg('Lock time elapsed, removing file')
            try:
                os.remove(self.lock_filename)
                if not os.path.exists(self.lock_filename):
                    self.log_msg('Lock File removed successfully')
            except:
                self.log_msg("WARNING: Could not remove lock file, remove manually or restart Wah!Cade")
                
        # If returning from a game rather than something like ALT+Tab
        if self.launched_game:
            self.message.hide()
            self.launched_game = False
            # Call log_in with any RFID's that were scanned while MAME had control
            if self.connected_to_arduino:
                while not self.log_in_queue.empty():
                    self.main_log = True
                    self.log_in(self.log_in_queue.get())
                    self.main_log = False
            # If the game supports high scores run the HiToText executions
            if self.current_rom in self.supported_games and len(self.current_players) != 0:
                htt_command = self.htt_read
                if not onWindows:
                    htt_command = "mono " + self.htt_read
                high_score_string = commands.getoutput(htt_command + "hi" + sep + self.current_rom + ".hi")
                if 'Error' in high_score_string: #'Error' indicates there is no .hi file but created .nv file instead
                    high_score_string = commands.getoutput(htt_command + "nvram" + sep + self.current_rom + ".nv")
                if not 'Error' in high_score_string and high_score_string != '' and not 'Exception' in high_score_string:
                    valid_string = ''
                    for i in high_score_string: #Some games support their own encoding, this bypasses that by only accepting ascii characters
                        if (ord(i)<128 and ord(i)>31) or ord(i) == 13 or ord(i) == 10:
                            valid_string += i
                        else:
                            valid_string += '?'
                    high_score_string = valid_string
                    if self.connected_to_server:
                        self.parse_high_score_text(high_score_string)
                else:
                    print "Unable to read the high score using HiToText"
        self.on_sclGames_changed()

    def on_winMain_focus_out(self, *args):
        """Window lost focus"""
        self.pointer_grabbed = False
        gtk.gdk.pointer_ungrab()
    
    def setup_video_chat(self):
        if self.video_chat.enabled:
            self.vc_feeds = []
            self.new_vc_feeds = []
            self.video_chat.setup_video_streamer()
            try:
                # Send the local IP to the server
                if self.video_chat.localip != "" or self.video_chat.localip != None:
                    post_data = {"ipAddress":self.video_chat.localip, "port":self.video_chat.localport}
                    requests.post(self.connection_url, post_data, headers=self.authorization)
                
                self.connection_time_running = False
                self.stop_test_connection_timers = False
                
                data = fromstring(requests.get(self.connection_url, headers=self.authorization).text)
                self.vc_feeds = [(info.find('ipAddress').text, info.find('port').text) for info in data.getiterator('connection')]
                self.new_vc_feed_updated = False
                self.manualVCMode = False
                
                self.on_connection_timer()
                self.start_timer('connection')
                self.start_timer('tstconnect')
            except:
                self.connected_to_server = False
        else:
            print "Video chat is disabled because no camera was found or connection issues."
    
    def start_video_chat(self):
        if not self.video_chat.receiver_running:
            self.video_chat.setup_video_receiver()
        
        self.vc_caption.set_text("...Loading... ")
        
        self.vid_container.show_all()
        self.imgArtwork1.hide()  
        self.video_chat.start_receiver()

        if not self.connection_time_running:
            self.start_timer('connection')
        
        if self.video_chat.is_loopback():
            self.vc_caption.set_text("Showing local video: " + str(self.video_chat.get_remote_info()))
#            print "Showing local video: " + str(self.video_chat.get_remote_info())
        else:
            self.vc_caption.set_text("Chatting with " + str(self.video_chat.get_remote_info()))
#            print "Chatting with: " + str(self.video_chat.get_remote_info())
    
    def stop_video_chat(self):
        self.vid_container.hide_all()
        self.imgArtwork1.show()
        self.video_chat.stop_receiver()
        
    
    def valid_remote_ip(self, remoteip, remoteport):
        try:
            import urllib2
            urllib2.urlopen('http://' + remoteip + ":" + remoteport, timeout=1)
            return True
        except:
            return False
    
    def next_video_feed(self):
        #find the current IP in the list
        current = self.find_in_feed_list(self.video_chat.remoteip)
        if current == -1:
            print "Couldn't find the current IP address in the current list. This shouldn't happen."
            return -1, -1 #this should never happen
        if self.new_vc_feed_updated:
            self.new_vc_feed_updated = False
            #find the current ip in the new list
            new_feed = self.find_in_new_feed_list(self.video_chat.remoteip)
            
            #if the ip isn't in the new list, search for a reference ip that is in both lists
            if new_feed == -1:
                for index in range(current - 1,0,-1):
                    ip = self.vc_feeds[index][0]
                    new_feed = self.find_in_new_feed_list(ip)
                    if new_feed != -1:
                        break
            
            #all previous IPs were removed, show the first video on the list
            if new_feed == -1:
                new_feed = 0 
            
            #update the feed list
            self.vc_feeds = self.new_vc_feeds
            current = new_feed
        
        #return the current video index and the one after it in a circular queue
        return current, ((current + 1) % len(self.vc_feeds))
                
    def find_in_new_feed_list(self, value):
        new_feed = -1
        for pos, info in enumerate(self.new_vc_feeds):
            if info[0] == value:
                new_feed = pos
                break
        return new_feed
    
    def find_in_feed_list(self, value):
        current = -1
        for pos, info in enumerate(self.vc_feeds):
            if info[0] == value:
                current = pos
                break
        return current
        
    def clean_up_video_chat(self):
        if self.connected_to_server and self.video_chat and self.video_chat.enabled:
            self.video_chat.kill_pipelines()
            try:
                requests.delete(self.connection_url + self.video_chat.localip, headers=self.authorization)
            except:
                self.connected_to_server = False
            self.stop_test_connection_timers = True
       
    def parse_high_score_text(self, text_string):
        """Parse the text file for high scores. 0 scores are not sent"""
        if len(self.current_players) > 1:
            multiple_score_list = []
        high_score_table = {}
        in_table = False #Some high scores start with 1 or more random lines, this keeps track when we get to high scores
        for line in iter(text_string.splitlines()): #Go through each line of the the high score result
            line = line.split('|')
            if "RANK" in line or "SCORE" in line or "NAME" in line or "ROUND" in line or in_table: #If we are in the table
                if line[0] != '':
                    if not in_table: #First line of table is the format line
                        _format = line
                        in_table = True
                        for column in line:
                            high_score_table[column] = '' # Initialize dictionary values of table (eg. Rank, Name, Score)
                    else: #not the first (formatting) line
                        if len(self.current_players) == 1:
                            for i in range(0, len(line)): # Go to length of line rather than format because format can be wrong sometimes
                                high_score_table[_format[i]] = line[i].rstrip() #remove whitespace
                            if 'SCORE' in high_score_table: # If high score table has score
                                if high_score_table['SCORE'] is not '0': # and score is not 0, check if player exists in DB
                                    if 'NAME' in high_score_table:
                                        post_data = {"score": high_score_table['SCORE'], "arcadeName":high_score_table['NAME'], "cabinetID": self.cabinet_name, "game":self.current_rom, "player":self.lblUsers.get_text()}                         
                                    else:
                                        post_data = {"score": high_score_table['SCORE'], "arcadeName":"", "cabinetID": self.cabinet_name, "game":self.current_rom, "player":self.current_players[0]}
                                    try:
                                        requests.post(self.score_url, post_data, headers=self.authorization)
                                    except:
                                        self.connected_to_server = False
                        else: #Handle multiple players
                            for i in range(0, len(line)): # Go to length of line rather than format because format can be wrong sometimes
                                high_score_table[_format[i]] = line[i].rstrip()
                            if 'SCORE' in high_score_table: # If high score table has score
                                if high_score_table['SCORE'] is not '0': # and score is not 0, check if player exists in DB                                                                
                                    if 'NAME' in high_score_table:
                                        post_data = {"score": high_score_table['SCORE'], "arcadeName":high_score_table['NAME'], "cabinetID": self.cabinet_name, "game":self.current_rom, "player":""}                         
                                        multiple_score_list.append(post_data)
                                    else:
                                        post_data = {"score": high_score_table['SCORE'], "arcadeName":"", "cabinetID": self.cabinet_name, "game":self.current_rom, "player":""}
                                        multiple_score_list.append(post_data)
            else: #Have not found the high score table yet
                continue

        if len(self.current_players) > 1 and len(multiple_score_list) > 0:
            self.upload_queue = []
            self.score_processing_queue = []
            
            for score in multiple_score_list:
                self.score_processing_queue.append(score)
            # Set the labels for display
            self.player_select.lbl1.set_text(self.score_processing_queue[len(self.score_processing_queue)-1]['score'] + "   " + self.score_processing_queue[len(self.score_processing_queue)-1]['arcadeName'])               
            self.show_window('playerselect')
            self.player_select.sclPlayers._update_display()
                

    def close_player_select(self, widget, data = None):
        """When the player select screen closes, this method starts"""
        if len(self.score_processing_queue) > 0:
            if self.selected_player != '': #Will be '' if user cancles the score
                score_to_associate = self.score_processing_queue.pop()
                score_to_associate['player'] = self.selected_player
                self.upload_queue.append(score_to_associate)
                self.selected_player = ''
                if len(self.score_processing_queue) > 0:
                    self.player_select.lbl1.set_text(self.score_processing_queue[len(self.score_processing_queue)-1]['score'] + "   " + self.score_processing_queue[len(self.score_processing_queue)-1]['arcadeName'])               
                    self.show_window('playerselect')
                    self.player_select.sclPlayers._update_display()
            else:
                if len(self.score_processing_queue) > 1:
                    self.score_processing_queue.pop()
                    self.player_select.lbl1.set_text(self.score_processing_queue[len(self.score_processing_queue)-1]['score'] + "   " + self.score_processing_queue[len(self.score_processing_queue)-1]['arcadeName'])               
                    self.show_window('playerselect')
                    self.player_select.sclPlayers._update_display()
                    return
                else:
                    self.score_processing_queue.pop()
        if len(self.score_processing_queue) == 0:
            self.hide_window('playerselect')
            if len(self.upload_queue) != 0:
                self.post_upload()
            else:
                self.current_window = 'main'
                self.winMain.present()
            return
        
    def post_upload(self):
        """Post data for multiple players"""
        try:
            while self.upload_queue:
                to_upload = self.upload_queue.pop()            
                requests.post(self.score_url, to_upload, headers=self.authorization)
            self.current_window = 'main'
            self.winMain.present()
            self.score_processing_queue = []
            self.upload_queue = []
        except:
            self.connected_to_server = False

             
    def check_connection(self, status_code):
        if ((status_code - 200) < 100 and (status_code - 200) >= 0) or status_code == 500:
            self.connected_to_server = True
#            print "Successfully connected to", self.props['host'] + ":" + self.props['port'] + "/" + self.props['db']
        else:
            self.connected_to_server = False
#            print "Failed to connect to", self.props['host'] + ":" + self.props['port'] + "/" + self.props['db'] + ", Status Code:", status_code
             
    def log_in(self, player_rfid):
        """Logs a player in"""
        self.selected_player = '' # resets self.selected_player for later use
        player_name = ''
        if player_rfid == "Manual Login": # If the player logs in with backslash
            # Because we are using the identify window rather than creating a new one we have to temporariy overwrite this list
            old_list = self.identify.sclIDs.ls
            self.identify.sclIDs.ls = []
            for v in self.player_info:
                self.identify.sclIDs.ls.append(v[0])
            self.identify.sclIDs.ls.sort()
            if not self.connected_to_arduino:
                # Add an option to register a new player
                self.identify.sclIDs.ls.insert(0, "Register New Player") #TODO: Is this neccessary?
            self.show_window('identify')
            self.identify.setRFIDlbl(player_rfid)
            self.identify.sclIDs.set_selected(1)
            self.identify.sclIDs._update_display()
            self.identify.set_lbls("", "Manually Logging In")
            while self.current_window == 'identify':
                self.wait_with_events(0.01)
            self.identify.set_lbls()
            if not self.connected_to_arduino:
                if self.selected_player == "Register New Player":
                    self.identify.sclIDs.ls = old_list
                    self.register_new_player(str(1)) #Register new player with ID of 1 to keep track of nonRFID users

            for v in self.player_info:
                if v[0] == self.selected_player:
                    player_rfid = v[1]
                    break
            self.selected_player = ''
            self.identify.sclIDs.ls = old_list
            if player_rfid == "Manual Login":
                print "No name selected, not logging in"
                return
        if self.recent_log and self.last_log == player_rfid: # Prevents the reader from logging someone in and then out immediately
            return
        if not self.timer_existing:
            self.timer_existing = True
            self.start_timer('login')
        for v in self.player_info:
            if v[1] == player_rfid:
                player_name = v[0]
                break
        if player_name in self.current_players: # If player is logged in, log them out
            self.recent_log = True
            self.last_log = player_rfid
            self.log_out(player_name)
        elif player_name != '': # Log the player in
            self.recent_log = True
            self.last_log = player_rfid
            self.current_players.append(player_name)
            if self.lblUsersLoggedOut.get_visible():
                self.lblUsersLoggedOut.hide()
            self.lblUsersLoggedIn.set_text(player_name + " has logged in.")
            self.lblUsersLoggedIn.show()
            self.timeLoginShown = time.time()
            self.lblUsers.set_text(self.get_logged_in_user_string(self.current_players))
        else: # If player doesn't exist then add them to DB
            self.register_new_player(player_rfid)
            if self.name_not_given:
                self.recent_log = True
                self.last_log = player_rfid
                if not self.timer_existing:
                    self.timer_existing = True
                    self.start_timer('login')
                return
            self.log_in(player_rfid)
            
    def log_out(self, player_name = "All"):
        """Logs a player out"""
        if player_name == "All":
            self.current_players = []
            if self.lblUsersLoggedIn.get_visible():
                self.lblUsersLoggedIn.hide()
            self.lblUsersLoggedOut.set_text("All users have been logged out.")
            self.lblUsersLoggedOut.show()
            self.timeLogoutShown = time.time()
        else:
            self.current_players.remove(player_name)
            if self.lblUsersLoggedIn.get_visible():
                self.lblUsersLoggedIn.hide()
            self.lblUsersLoggedOut.set_text(player_name + " has logged out.")
            self.lblUsersLoggedOut.show()
            self.timeLogoutShown = time.time()
        if self.current_players == []:
            self.lblUsers.set_text("Not logged in")
        else:
            self.lblUsers.set_text(self.get_logged_in_user_string(self.current_players))
            
    def register_new_player(self, player_rfid):
        """Add a new player to the database"""
        self.show_window('identify')
        if player_rfid == "1":
            self.identify.setRFIDlbl("Manually Logging In")
        else:
            self.identify.setRFIDlbl(player_rfid)
        self.identify.sclIDs._update_display()
        while self.current_window == 'identify':
            if self.main_log == True:
                self.wait_with_events(0.01)
            else:
                time.sleep(0.01)
        player_name = self.selected_player
        
        #If user originally registered manually, change their ID to their RFID
        if (player_name, '1') in self.player_info and player_rfid != '1':
            post_data = {"playerId":1, "name":player_name, "player.playerID": player_rfid}
            try:
                requests.put(self.player_url, post_data, headers=self.authorization)
            except:
                self.connected_to_server = False
            return
        
        if player_name != 'Register New Player' and player_name != '':
            self.player_info.append([player_name, player_rfid])
            post_data = {"name":player_name, "playerID":player_rfid}
            try:
                requests.post(self.player_url, post_data, headers=self.authorization)
            except:
                self.connected_to_server = False
                return
            self.identify.sclIDs.ls.remove(player_name)
            self.name_not_given = False
        else:
            print "No player name given, not updating lists"
            self.name_not_given = True                
        
    def get_logged_in_user_string(self, current_users):
        """Get string containing names of loged in users"""
        s = ''
        for index, user in enumerate(reversed(current_users)):
            if index == 0:
                s += user
            elif index > 3:
                s += ", ..."
                break
            else:
                s += ", " + user
        return s

    def reset_recent_log(self):
        """Reset's vars for preventing a user from rapidly logging in"""
        self.recent_log = False
        self.timer_existing = False

    def on_winMain_key_press(self, widget, event, *args):
        """Respond to key presses"""
        if not os.path.exists(self.lock_filename):
            current_window = self.current_window
            mw_keys = []
            mw_key = ''
            mw_func = ''
            mw_functions = []
            joystick_key = None
            if len(args) > 1:
                if args[0] == "JOYSTICK":
                    joystick_key = args[1]
                    if debug_mode:
                        self.log_msg("on_winMain_key_press: joystick:" + str(joystick_key),1)
            # Reset screen saver time (and turn off if necessary)
            self.scrsave_time = time.time()
            if self.scrsaver.running:
                self.scrsaver.stop_scrsaver()
                #print "on_winMain_key_press: callifile_listsng start timer"
                self.start_timer('scrsave')
                self.start_timer('portal')
            if event.type == gtk.gdk.MOTION_NOTIFY and self.pointer_grabbed:
                # Mouse moved
                x, y = event.get_coords()
                dx = x - self.old_mouse[0]
                dy = y - self.old_mouse[1]
                if abs(dx) >= abs(dy):
                    # X-axis
                    mm = dx
                    if mm < -3.0:
                        mw_keys = ['MOUSE_LEFT']
                    elif mm > 3.0:
                        mw_keys = ['MOUSE_RIGHT']
                else:
                    # Yy-axis
                    mm = dy
                    if mm < -3.0:
                        mw_keys = ['MOUSE_UP']
                    elif mm > 3.0:
                        mw_keys = ['MOUSE_DOWN']
                self.scroll_count += int(abs(mm) / 10) + 1
                if not mw_keys:
                    self.scroll_count = 0
                    self.chat_key_count = 0
                    if widget == self.winMain:
                        self.sclGames.update()
                    return
                # Warp pointer - stops mouse hitting screen edges
                winpos = self.winMain.get_position()
                self.old_mouse = (200, 200)
                self.display.warp_pointer(self.screen, winpos[0] + 200, winpos[1] + 200)
            elif event.type == gtk.gdk.BUTTON_RELEASE:
                # Mouse click
                mw_keys = ['MOUSE_BUTTON%s' % (event.button - 1)]
            elif event.type == gtk.gdk.SCROLL:
                self.scroll_count = 0
                self.chat_key_count = 0
                # Mouse scroll wheel
                if event.direction in [gtk.gdk.SCROLL_UP, gtk.gdk.SCROLL_LEFT]:
                    mw_keys = ['MOUSE_SCROLLUP']
                elif event.direction in [gtk.gdk.SCROLL_DOWN, gtk.gdk.SCROLL_RIGHT]:
                    mw_keys = ['MOUSE_SCROLLDOWN']
                else:
                    return
            elif event.type == gtk.gdk.KEY_PRESS:
                if debug_mode:
                    self.log_msg("  key-press",1)
                if joystick_key:
                    # Joystick action
                    mw_keys = [joystick_key]
                else:
                    # Keyboard pressed, get GTK keyname
                    keyname = gtk.gdk.keyval_name(event.keyval).lower()
                    # Got something?
                    if keyname not in mamewah_keys:
                        return
                    # Get mamewah keyname
                    mw_keys = mamewah_keys[keyname]
                    if mw_keys == []:
                        return
            elif event.type == gtk.gdk.KEY_RELEASE:
                self.scroll_count = 0
                self.chat_key_count = 0
                # Updates ROM image after scrolling stops
                if len(self.lsGames) != 0:
                    game_info = filters.get_game_dict(self.lsGames[self.sclGames.get_selected()])
                    for i, img in enumerate(self.visible_img_list):
                        if self.scroll_count == 0:
                            img_filename = self.get_artwork_image(
                                self.visible_img_paths[i],
                                self.layout_path,
                                game_info,
                                self.current_emu,
                                (i + 1))
                            self.display_scaled_image(img, img_filename, self.keep_aspect, img.get_data('text-rotation'))
                self.on_sclGames_changed()
                self.gamesScrollOverlay.hide()
                self.IDsScrollOverlay.hide()
                # Keyboard released, update labels, images, etc
                if widget == self.winMain:
                    # Only update if no further events pending
                    self.sclGames.update()
                    if old_keyb_events:
                        if debug_mode:
                            self.log_msg("  key-release",1)
                        self.sclGames.update()
                    elif not gtk.gdk.events_pending():
                        if debug_mode:
                            self.log_msg("  key-release",1)
                        self.sclGames.update()
                if joystick_key:
                    # Don't need "release" joystick actions to be executed
                    mw_keys = []
                    if debug_mode:
                        self.log_msg("  joystick: cleared_events",1)
            # Get mamewah function from key
            for mw_key in mw_keys:
                mw_functions = self.ctrlr_ini.reverse_get(mw_key)
                if mw_functions:
                    break
            for mw_func in mw_functions:
                # Which function?
                if mw_func == 'ID_SHOW' and current_window == 'main' and self.identify.ldap.LDAP_connected and self.connected_to_server:  # Show identify window any time
#                    if self.connected_to_arduino:
                    self.main_log = True
                    self.log_in("Manual Login")
                    self.main_log = False
#                    else:
#                        self.show_window('identify')
#                        self.identify.sclIDs._update_display()
                if mw_func == 'BACK' and current_window != 'main':
                    self.hide_window(current_window)
                if current_window == 'main':
                    # Display first n letters of selected game when scrolling quickly
                    if self.scroll_count > self.showOverlayThresh:
                        overlayLetters = self.lsGames[ self.sclGames.get_selected() ][ GL_GAME_NAME ][ 0 : self.gamesScrollOverlay.charShowCount ]
                        self.gamesScrollOverlay.set_markup( _('%s%s%s') % (self.gamesOverlayMarkupHead, overlayLetters, self.gamesOverlayMarkupTail) )
                        self.gamesScrollOverlay.show()
                    # Main form
                    if mw_func == 'UP_1_GAME':
                        self.scroll_count += 1
                        self.play_clip('UP_1_GAME')
                        self.sclGames.scroll((int(self.scroll_count / 20) * -1) - 1)
                    elif mw_func == 'DOWN_1_GAME':
                        self.scroll_count += 1
                        self.play_clip('DOWN_1_GAME')
                        self.sclGames.scroll(int(self.scroll_count / 20) + 1)
                    elif mw_func == 'UP_1_PAGE':
                        self.scroll_count += 1
                        self.play_clip('UP_1_PAGE')
                        self.sclGames.scroll(-self.sclGames.num_rows)
                    elif mw_func == 'DOWN_1_PAGE':
                        self.scroll_count += 1
                        self.play_clip('DOWN_1_PAGE')
                        self.sclGames.scroll(+self.sclGames.num_rows)
                    elif mw_func == 'UP_1_LETTER':
                        self.scroll_count += 1
                        self.play_clip('UP_1_LETTER')
                        self.sclGames.jumpToLetter(mw_func)
                    elif mw_func == 'DOWN_1_LETTER':
                        self.scroll_count += 1
                        self.play_clip('DOWN_1_LETTER')
                        self.sclGames.jumpToLetter(mw_func)
                    elif mw_func == 'RANDOM_GAME':
                        self.play_clip('RANDOM_GAME')
                        self.sclGames.set_selected(self.get_random_game_idx())
                    elif mw_func == 'FIND_GAME':
                        self.play_clip('FIND_GAME')
                        self.options.set_menu('find')
                        self.show_window('options')
                    elif mw_func == 'ADD_GAME_TO_LIST':
                        self.play_clip('ADD_GAME_TO_LIST')
                        self.options.set_menu('add_to_list')
                        self.show_window('options')
                    elif mw_func == 'REMOVE_GAME_FROM_LIST':
                        self.play_clip('REMOVE_GAME_FROM_LIST')
                        self.remove_current_game()
                    elif mw_func == 'LAUNCH_GAME':
                        if len(self.lsGames) != 0:
                            self.play_clip('LAUNCH_GAME')
                            self.launch_auto_apps_then_game(self.lsGames[self.sclGames.get_selected()][1])
                    elif mw_func == 'LAUNCH_GAME_WITH_OPTIONS1':
                        self.play_clip('LAUNCH_GAME_WITH_OPTIONS1')
                        self.launch_auto_apps_then_game([g[1] for g in self.lsGames if g[0]==self.sclGames.get_selected_item()][0], 
                            self.emu_ini.get('alt_commandline_format_1'))
                    elif mw_func == 'LAUNCH_GAME_WITH_OPTIONS2':
                        self.play_clip('LAUNCH_GAME_WITH_OPTIONS2')
                        self.launch_auto_apps_then_game([g[1] for g in self.lsGames if g[0]==self.sclGames.get_selected_item()][0], 
                            self.emu_ini.get('alt_commandline_format_2'))
                    elif mw_func == 'MENU_SHOW':
                        self.play_clip('MENU_SHOW')
                        self.options.set_menu('main')
                        self.show_window('options')
                        self.options.sclOptions._update_display()
                    elif mw_func == 'SELECT_EMULATOR':
                        self.play_clip('SELECT_EMULATOR')
                        self.options.set_menu('emu_list')
                        self.show_window('options')
                    elif mw_func == 'NEXT_EMULATOR':
                        self.play_clip('NEXT_EMULATOR')
                        emu_list = [e[1] for e in self.emu_lists]
                        emu_idx = emu_list.index(self.current_emu)
                        if emu_idx < len(emu_list) - 1:
                            emu_idx += 1
                        else:
                            emu_idx = 0
                        self.load_emulator(emu_list[emu_idx])
                    elif mw_func == 'PREVIOUS_EMULATOR':
                        self.play_clip('PREVIOUS_EMULATOR')
                        emu_list = [e[1] for e in self.emu_lists]
                        emu_idx = emu_list.index(self.current_emu)
                        if emu_idx > 0:
                            emu_idx -= 1
                        else:
                            emu_idx = len(emu_list) - 1
                        self.load_emulator(emu_list[emu_idx])
                    elif mw_func == 'SELECT_GAMELIST':
                        self.play_clip('SELECT_GAMELIST')
                        self.options.set_menu('game_list')
                        self.show_window('options')
                    elif mw_func == 'NEXT_GAMELIST':
                        self.play_clip('NEXT_GAMELIST')
                        self.current_list_idx = self.get_next_list_in_cycle(+1)
                        self.load_list()
                    elif mw_func == 'PREVIOUS_GAMELIST':
                        self.play_clip('PREVIOUS_GAMELIST')
                        self.current_list_idx = self.get_next_list_in_cycle(-1)
                        self.load_list()
                    elif mw_func == 'ROTATE_SCREEN_TOGGLE':
                        self.play_clip('ROTATE_SCREEN_TOGGLE')
                        self.load_layouts('toggle')
                    elif mw_func == 'ROTATE_SCREEN_0':
                        self.play_clip('ROTATE_SCREEN_0')
                        self.load_layouts(0)
                    elif mw_func == 'ROTATE_SCREEN_90':
                        self.play_clip('ROTATE_SCREEN_90')
                        self.load_layouts(90)
                    elif mw_func == 'ROTATE_SCREEN_180':
                        self.play_clip('ROTATE_SCREEN_180')
                        self.load_layouts(180)
                    elif mw_func == 'ROTATE_SCREEN_270':
                        self.play_clip('ROTATE_SCREEN_270')
                        self.load_layouts(270)
                    elif mw_func == 'NEXT_TRACK':
                        self.play_clip('NEXT_TRACK')
                        if self.music_enabled:
                            self.gstMusic.next_track()
                    elif mw_func == 'PREVIOUS_TRACK':
                        self.play_clip('PREVIOUS_TRACK')
                        if self.music_enabled:
                            self.gstMusic.previous_track()
                    elif mw_func == 'LAUNCH_APP_1':
                        self.play_clip('LAUNCH_APP_1')
                        self.external_app_queue = []
                        self.launch_external_application(1)
                    elif mw_func == 'LAUNCH_APP_2':
                        self.play_clip('LAUNCH_APP_2')
                        self.external_app_queue = []
                        self.launch_external_application(2)
                    elif mw_func == 'LAUNCH_APP_3':
                        self.play_clip('LAUNCH_APP_3')
                        self.external_app_queue = []
                        self.launch_external_application(3)
                    elif mw_func == 'EXIT_TO_WINDOWS':
                        self.play_clip('EXIT_TO_WINDOWS')
                        self.exit_wahcade()
                    elif mw_func == 'EXIT_WITH_CHOICE':
                        self.play_clip('EXIT_WITH_CHOICE')
                        self.options.set_menu('exit')
                        self.show_window('options')
                    elif mw_func == 'LOG_OUT':
                        if self.current_players:
                            self.log_out()
                    elif mw_func == 'TOGGLE_VIDEO':
                        self.chat_key_count += 1
                        if self.connected_to_server and self.video_chat and self.video_chat.enabled:
                            if self.chat_key_count == 1:
                                if self.vid_container.get_property("visible") == False:
                                    self.setup_video_chat()
                                    self.start_video_chat()
                                else:
                                    self.stop_video_chat()
                                    self.clean_up_video_chat()
                        else:
                            print "Video Chat is disabled (you are not connected to the server or no camera was found)."
                    elif mw_func == 'NEXT_VIDEO':
                        if not self.video_chat_enabled:
                            return
                        current, new_feed = self.next_video_feed()
                        if new_feed == current: #there is only one video or an error occured
                            self.manualVCMode = False
                        else:
                            info = self.vc_feeds[new_feed]
                            self.manualVCMode = True
                            self.video_chat.set_remote_info(info[0], info[1])
                            self.stop_video_chat()
                            self.start_video_chat()
                        
                elif current_window == 'options':
                    if mw_func == 'OP_UP_1_OPTION':
                        self.play_clip('OP_UP_1_OPTION')
                        self.options.sclOptions.scroll(-1)
                    elif mw_func == 'OP_DOWN_1_OPTION':
                        self.play_clip('OP_DOWN_1_OPTION')
                        self.options.sclOptions.scroll(+1)
                    elif mw_func == 'OP_UP_1_OPTION_PAGE':
                        self.play_clip('OP_UP_1_OPTION_PAGE')
                        self.options.sclOptions.scroll(-self.options.sclOptions.num_rows)
                    elif mw_func == 'OP_DOWN_1_OPTION_PAGE':
                        self.play_clip('OP_DOWN_1_OPTION_PAGE')
                        self.options.sclOptions.scroll(+self.options.sclOptions.num_rows)
                    elif mw_func == 'OP_MENU_SELECT':
                        self.play_clip('OP_MENU_SELECT')
                        self.options.menu_selected()
                    elif mw_func == 'OP_MENU_HIDE':
                        self.hide_window('options')
                    elif mw_func == 'OP_MENU_BACK':
                        self.play_clip('OP_MENU_BACK')
                        if self.options.current_menu == 'main':
                            self.hide_window('options')
                        elif self.options.current_menu in ['emu_list', 'game_list', 'list_options', 'record_video', 'music', 'exit']:
                            self.options.set_menu('main')
                        elif self.options.current_menu == 'add_to_list':
                            self.options.set_menu('list_options')
                        elif self.options.current_menu == 'generate_ftr':
                            if self.current_filter_changed:
                                # Generate new filter
                                self.options.set_menu('generate_new_list')
                            else:
                                self.options.set_menu('list_options')
                        elif self.options.current_menu.startswith('ftr:'):
                            self.options.set_menu('generate_ftr')
                        elif self.options.current_menu == 'find':
                            self.options.find_game('back')
                        elif self.options.current_menu == 'music_dir':
                            self.options.set_menu('music')
                elif current_window == 'scrsaver':
                    # Screensaver
                    if mw_func == 'SS_FIND_N_SELECT_GAME':
                        self.sclGames.set_selected(self.scrsaver.game_idx)
                    # Stop intro / exit movie playing if any key is pressed
                    if self.scrsaver.movie_type in ('intro', 'exit'):
                        self.scrsaver.video_player.stop()
                # History viewer
                elif current_window == 'history':
                    if mw_func == 'UP_1_GAME':
                        self.play_clip('UP_1_GAME')
                        self.histview.sclHistory.scroll((int(self.scroll_count / 20) * -1) - 1)
                    elif mw_func == 'DOWN_1_GAME':
                        self.play_clip('DOWN_1_GAME')
                        self.histview.sclHistory.scroll(int(self.scroll_count / 20) + 1)
                    elif mw_func in ['UP_1_PAGE', 'UP_1_LETTER']:
                        self.play_clip('UP_1_PAGE')
                        self.histview.sclHistory.scroll(-self.histview.sclHistory.num_rows)
                    elif mw_func in ['DOWN_1_PAGE', 'DOWN_1_LETTER']:
                        self.play_clip('DOWN_1_PAGE')
                        self.histview.sclHistory.scroll(+self.histview.sclHistory.num_rows)
                    elif mw_func in [
                            'EXIT_TO_WINDOWS',
                            'LAUNCH_APP_%s' % self.histview.app_number,
                            'LAUNCH_GAME']:
                        self.hide_window('history')
                        self.auto_launch_external_app()
                # Control panel viewer
                elif current_window == 'cpviewer':
                    if mw_func in [
                            'EXIT_TO_WINDOWS',
                            'LAUNCH_APP_%s' % self.cpviewer.app_number,
                            'LAUNCH_GAME']:
                        self.hide_window('cpviewer')
                        self.auto_launch_external_app()
                # Message window
                elif current_window == 'message':
                    if self.message.wait_for_key:
                        self.message.hide()
                # Identify window
                elif current_window == 'identify':
                    # Display first n letters of selected name when scrolling quickly
                    if self.scroll_count > self.showOverlayThresh:
                        overlayLetters = self.identify.sclIDs.ls[ self.identify.sclIDs.get_selected() ][ 0 : self.IDsScrollOverlay.charShowCount ]
                        self.IDsScrollOverlay.set_markup( _('%s%s%s') % (self.IDsOverlayMarkupHead, overlayLetters, self.IDsOverlayMarkupTail) )
                        self.IDsScrollOverlay.show()
                    # Exit from identify window
                    if mw_func in ['ID_BACK']:
                        self.selected_player = ''
                        self.hide_window('identify')
                    elif mw_func in ['ID_SELECT']:
                        self.selected_player = self.identify.sclIDs.ls[self.identify.sclIDs.get_selected()]
                        self.hide_window('identify')
                    elif mw_func in ['ID_UP_1_NAME']:
                        self.identify.sclIDs.scroll((int(self.scroll_count / 20) * -1) - 1)
                    elif mw_func in ['ID_DOWN_1_NAME']:
                        self.identify.sclIDs.scroll(int(self.scroll_count / 20) + 1)
                    elif mw_func == 'ID_UP_1_LETTER':
                        self.play_clip('UP_1_LETTER')
                        self.identify.sclIDs.jumpToLetter(mw_func)
                    elif mw_func == 'ID_DOWN_1_LETTER':
                        self.play_clip('DOWN_1_LETTER')
                        self.identify.sclIDs.jumpToLetter(mw_func)
                elif current_window == 'playerselect':
                    if mw_func in ['PS_BACK']:
                        self.selected_player = ''
                        self.hide_window('playerselect')
                        self.close_player_select(self.player_select)
                    # Exit from identity window
                    elif mw_func in ['PS_SELECT']:
                        self.selected_player = self.player_select.sclPlayers.ls[self.player_select.sclPlayers.get_selected()]
                        self.hide_window('playerselect')
                        self.close_player_select(self.player_select)
                    # Scroll up 1 name
                    elif mw_func in ['PS_UP_1_NAME']:
                        self.player_select.sclPlayers.scroll((int(self.scroll_count / 20) * -1) - 1)
                    # Scroll down 1 name
                    elif mw_func in ['PS_DOWN_1_NAME']:
                        self.player_select.sclPlayers.scroll(int(self.scroll_count / 20) + 1)
            # Force games list update if using mouse scroll wheel
            if 'MOUSE_SCROLLUP' in mw_keys or 'MOUSE_SCROLLDOWN' in mw_keys:
                if widget == self.winMain:
                    self.play_clip('UP_1_GAME')
                    self.sclGames.update()

    def on_sclGames_changed(self, *args):
        """Game selected"""
        self.game_ini_file = None
        self.stop_video()
        if self.sclGames.get_selected() > self.lsGames_len - 1:
            # Blank labels & images
            for img in self.visible_img_list:
                img.set_from_file(None)
            for lbl in self._main_labels:
                lbl.set_text('')
            return
        # Set current game in ini file
        self.current_list_ini.set('current_game', self.sclGames.get_selected())
        # Get info to display in bottom right box
        if not self.lsGames: # Fixes error when switching lists with empty games
            return
        game_info = filters.get_game_dict(self.lsGames[self.sclGames.get_selected()])
        self.current_rom = game_info['rom_name']
        # Check for game ini file
        game_ini_file = os.path.join(CONFIG_DIR, 'ini', '%s' % self.current_emu, '%s' % game_info['rom_name'] + '.ini' )
        if os.path.isfile(game_ini_file):
            self.log_msg(game_info['rom_name'] + " has custom ini file")
            self.game_ini_file = MameWahIni(game_ini_file)
        # Set layout text items
        self.lblGameDescription.set_text(game_info['game_name'])
        self.lblGameSelected.set_text(_('Game %s/%s') % (self.sclGames.get_selected() + 1, self.lsGames_len))
        if game_info['clone_of'] != '':
            rom_name_desc = _('%s (Clone of %s)') % (game_info['rom_name'], game_info['clone_of'])
        else:
            rom_name_desc = game_info['rom_name']
        # Set labels in the ROM info panel
        self.lblRomName.set_text(rom_name_desc)
        self.lblYearManufacturer.set_text('%s %s' % (game_info['year'], game_info['manufacturer']))
        self.lblScreenType.set_text('%s %s' % (game_info['screen_type'], game_info['display_type']))
        self.lblControllerType.set_text(game_info['controller_type'])
        self.lblDriverStatus.set_text('%s, %s, %s' % (
            game_info['driver_status'],
            game_info['colour_status'],
            game_info['sound_status']))
        self.lblCatVer.set_text(game_info['category'])
        # Get high score data and display it
        if self.scroll_count < self.showHighScoreThresh:    
            if not self.connected_to_server:
                self.lblHighScoreData.set_markup(_('%s%s%s') % (self.highScoreDataMarkupHead, " NOT CONNECTED TO A SERVER", self.highScoreDataMarkupTail))
            elif game_info['rom_name'] in self.supported_games:
                highScoreInfo = self.get_score_string()
                self.lblHighScoreData.modify_font(pango.FontDescription(self.highScoreDataLayout['font-name']))
                self.lblHighScoreData.set_text(highScoreInfo)
                self.lblHighScoreData.set_markup(_('%s%s%s') % (self.highScoreDataMarkupHead, highScoreInfo, self.highScoreDataMarkupTail))
            else:
                self.lblHighScoreData.set_markup(_('%s%s%s') % (self.highScoreDataMarkupHead, "  HIGH SCORE NOT SUPPORTED", self.highScoreDataMarkupTail))        
        else:
            self.lblHighScoreData.set_text("")
        # Start video timer
        if self.scrsaver.movie_type not in ('intro', 'exit'):
            self.start_timer('video')
        # Set layout images (at low scroll speeds)
        for i, img in enumerate(self.visible_img_list):
            # Don't display an image if starting to scroll quickly
            if self.scroll_count >= self.showImgThresh:
                img.set_from_file(None)
            else:
                img_filename = self.get_artwork_image(
                    self.visible_img_paths[i],
                    self.layout_path,
                    game_info,
                    self.current_emu,
                    (i + 1))
                self.display_scaled_image(img, img_filename, self.keep_aspect, img.get_data('text-rotation'))
        
    def get_score_string(self):
        """Parse Scores from DB into display string"""
        try:
            score_string = requests.get(self.game_url + self.current_rom + "/highscore", headers=self.authorization).text
        except:
            self.connected_to_server = False
            return " NOT CONNECTED TO A SERVER "
        index = 1
        if score_string != '[]' and "Could not find" not in score_string:
            score_string = score_string[1:-1] # Trim leading and trailing [] from string
            score_list = score_string.split(",")
            for s in score_list: #Check for off chance data didn't download properly
                if ':' not in s:
                    return
            score, name = zip(*(s.split(":") for s in score_list)) # Split the list into name's and scores
            score_list[:]=[]
            score_string = ''
            for pair in range(len(name)): # Take each name and score and tuple them together
                paring = (name[pair].encode('utf8').strip(), score[pair].encode('utf8'))
                score_list.append(paring)
            score_list = sorted(score_list, key = lambda score: int(score[1]), reverse = True) 
            for name, score in score_list:
                if index < 10: # Format for leading spaces by numbers. Makes 1. match up with 10.
                    score_string += " " + str(index) + ". "
                    score_string += '{0:<21}'.format(name) + '{0:>21}\n'.format(score)
                index += 1
            while index <= 10: # Fill in un-used score spots
                if index < 10:
                    score_string += " "
                score_string += str(index) + ". " + '{0:<21}'.format("-"*12) + '{0:>21}\n'.format("-"*9)
                index += 1
        else: # No high scores recorded
            score_string = ''
            while index <= 10:
                if index < 10:
                    score_string += " "
                score_string += str(index) + ". " + '{0:<21}'.format("-"*12) + '{0:>21}\n'.format("-"*9)
                index += 1
        return score_string
    
    def portal_timer(self):
        sound_time = random.randint((5*60), (15*60))
        if int(time.time() - self.portal_time_last_played) >= sound_time:
            if len(self.sounds) != 0:
                sound_file = self.sounds[random.randrange(0, len(self.sounds))]
                if str(sound_file).endswith(".wav") or str(sound_file).endswith(".mp3") or str(sound_file).endswith(".mp4"):
                    pygame.mixer.init() #Safe to call multiple times
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()
                    self.portal_time_last_played = time.time()
                    #pygame.mixer.quit #Use if you want to re-initialize mixer with different args
        return True
            
    def on_scrsave_timer(self):
        """Timer event - check to see if we need to start video or screen saver"""
        # Hide the label saying when a user logs in/out
        if int(time.time() - self.timeLogoutShown) >= self.hide_log_delay:
            self.lblUsersLoggedOut.hide()
        if int(time.time() - self.timeLoginShown) >= self.hide_log_delay:
            self.lblUsersLoggedIn.hide()
        # Use timer for screen saver to log a person out after period of inactivity
        if int(time.time() - self.scrsave_time) >= self.auto_logout_delay and self.current_players != []:
            self.log_out()
        # Need to start screen saver?
        if int(time.time() - self.scrsave_time) >= self.scrsave_delay:
            # Yes, stop any vids playing
            self.stop_video()
            # Closes any open windows
            if self.current_window != 'main':
                self.selected_player = ''
                self.hide_window('calledfromscreensaver')
            if self.emu_ini.get('saver_type') in ['blank_screen', 'slideshow', 'movie', 'launch_scr']:
                # Start screen saver
                self.scrsaver.start_scrsaver(self.emu_ini.get('saver_type'))
            else:
                print _("Error: wrong screen saver type: [%s]") % (self.emu_ini.get('saver_type'))
            return False
        # Done
        return True

    def on_video_timer(self):
        """Timer event - start video playing"""
        # Start video playing?
        if self.video_enabled and self.current_window == 'main':
            # Stop existing vid playing
            self.stop_video()
            # Something in the list?
            if self.lsGames_len == 0:
                return False
            # Get info
            vid_filename = self.get_video_file(
                self.emu_ini.get('movie_preview_path'),
                filters.get_game_dict(self.lsGames[self.sclGames.get_selected()]))
            #print "vid_filename=",vid_filename
            if os.path.isfile(vid_filename):
                # Resize video vidget
                self.video_playing = True
                img_w, img_h = self.video_artwork_widget.get_size_request() #@UnusedVariable
                xpos = (img_w - self.video_width) / 2
                self.fixd.move(
                    self.drwVideo,
                    self.fixd.child_get_property(self.video_artwork_widget.get_parent(), 'x') + xpos,
                    self.fixd.child_get_property(self.drwVideo, 'y'))
                self.drwVideo.set_size_request(self.video_width, self.video_height)
                self.drwVideo.set_property('visible', True)
                self.video_artwork_widget.set_property('visible', False)
                # Set volume
                if self.music_movies_mix == 'mute_movies':
                    vol = 0
                else:
                    vol = self.wahcade_ini.getint('movie_volume')
                self.video_player.set_volume(vol)
                # Start video
                self.video_player.play(vid_filename)
        # Done
        return False

    def stop_video(self):
        """Stop playing video and timer"""
        if self.video_timer:
            gobject.source_remove(self.video_timer)
        if self.video_playing:
            self.video_playing = False
            self.video_player.stop()
            self.drwVideo.set_property('visible', False)
            self.video_artwork_widget.set_property('visible', True)
            self.do_events()

    def get_next_list_in_cycle(self, direction):
        """Return index of next "cycleable" list in current emulator lists"""
        # Create array of available lists for current emulator
        file_lists = self.build_filelist("int", "ini", "(?<=-)\d+", self.current_emu, "-")
        current_idx = file_lists.index(self.current_list_idx) + direction
        # Find the next list then return number of list
        if current_idx == len(file_lists):
            new_idx = 0
        else:
            new_idx = file_lists[current_idx]
        return new_idx

    def launch_auto_apps_then_game(self, romName, game_cmdline_args=''):
        """Call any automatically launched external applications, then run currently selected game"""
        # If we did not get a valid romName, return immediately
        if not romName:
            return
        self.external_app_queue = self.emu_ini.get('auto_launch_apps').split(',')
        # Get it into correct order
        self.external_app_queue.reverse()
        if self.external_app_queue == ['']:
            self.external_app_queue = []
        while self.external_app_queue:
            self.auto_launch_external_app(True, game_cmdline_args)
        else:
            self.launch_game(romName, game_cmdline_args)

    def get_launch_options(self, opts):
        """Returns parsed command line options"""
        d = {}
        # Minimize?
        d['minimize_wahcade'] = ('{minimize}' in opts)
        d['play_music'] = ('{music}' in opts)
        if self.music_enabled and not d['play_music']:
            self.gstMusic.pause()
        # Replace markers with actual values
        selected_index = self.sclGames.get_selected()
        opts = opts.replace('[name]', self.lsGames[selected_index][GL_ROM_NAME])
        opts = opts.replace('[year]', self.lsGames[selected_index][GL_YEAR])
        opts = opts.replace('[manufacturer]', self.lsGames[selected_index][GL_MANUFACTURER])
        opts = opts.replace('[clone_of]', self.lsGames[selected_index][GL_CLONE_OF])
        opts = opts.replace('[display_type]', self.lsGames[selected_index][GL_DISPLAY_TYPE])
        opts = opts.replace('[screen_type]', self.lsGames[selected_index][GL_SCREEN_TYPE])
        opts = opts.replace('[category]', self.lsGames[selected_index][GL_CATEGORY])
        # Automatically rotate to emulator based on the [autorotate] flag being present.
        # This is typically for the MAME emulator since all other emulators known to work use a single orientation factor.
        screen_set = {0: '',
                      90: '-rol',
                      180: '-flipy',
                      270: '-ror'}
        opts = opts.replace('[autorotate]', screen_set[self.layout_orientation])
        opts = opts.replace('[rompath]', self.emu_ini.get('rom_path'))
        # If multiple rom extensions are used, check which file is correct
        # Will break after first file is found
        romext = self.check_ext_on_game_launch(self.emu_ini.get('rom_extension'))
        try:
            opts = opts.replace('[romext]', romext)
        except:
            opts = opts.replace('[romext]', "")
        opts = opts.replace('{minimize}', '')
        opts = opts.replace('{music}', '')
        d['options'] = opts
        # Done
        return d

    def launch_game(self, romName, cmdline_args=''):
        """Run currently selected game"""
        # Collect any memory "leaks"
        gc.collect()
        # Stop any vids playing
        self.stop_video()
        # Get rom name
        if self.lsGames_len == 0:
            return
        #rom = self.lsGames[self.sclGames.get_selected()][GL_ROM_NAME]
        rom = romName
        title = [g[0] for g in self.lsGames if g[1] == rom][0]
        # Show launch message
        self.message.display_message(
            _('Running...'),
            '%s: %s' % (rom, title))
        # Erase scores from hi score file of current game
        if rom in self.supported_games:
            htt_command = self.htt_erase
            if not onWindows:
                    htt_command = "mono " + self.htt_erase
            if os.path.exists(self.mame_dir + 'hi' + sep + rom + '.hi'):
                os.system(htt_command + 'hi' + sep + rom + '.hi')
            elif os.path.exists(self.mame_dir + 'nvram' + sep + rom + '.nv'):
                os.system(htt_command + 'nvram' + sep + rom + '.nv')
            else:
                print rom, 'high score file not found'
        # Stop joystick poller
        if self.joy is not None:
            self.joy.joy_count('stop')
            gobject.source_remove(self.joystick_timer)
        # Start timing
        time_game_start = time.time()
        # Wait a bit - to let message window display
        self.show_window('message')
        self.wait_with_events(0.25)
        # Get command line optio
        if cmdline_args:
            opts = cmdline_args
        else:
            if self.game_ini_file:
                opts = self.game_ini_file.get(
                    option = 'commandline_format',
                    default_value = self.emu_ini.get('commandline_format'))
            else:
                opts = self.current_list_ini.get(
                    option = 'commandline_format',
                    default_value = self.emu_ini.get('commandline_format'))
        game_opts = self.get_launch_options(opts)
        # Pause music?
        if self.music_enabled and not game_opts['play_music']:
            self.gstMusic.stop()    
        # Check emu exe
        emulator_executable = self.emu_ini.get('emulator_executable')
        # CHECK FOR LAUNCHER PLUGINS
        rom_extension = os.path.splitext(game_opts['options'])[1]
        pass_check = False
        wshell = True
        args = ""
        try:
            plugin = "launcher_" + rom_extension[1:]
            fp, filename, desc = imp.find_module(plugin,  ['./plugins'])
            mod = imp.load_module(plugin, fp, filename, desc)
            if mod:
                result = mod.read_scexec(game_opts['options'])
                emulator_executable = result[1].strip("\n")
                args = result[2].strip("\n")
                pass_check = result[4]
                wshell = result[5]
                self.log_msg('PLUGIN: %s' % result[0])
            if fp:
                fp.close()
        except:
            pass
        if not pass_check:
            if not os.path.isfile(emulator_executable):
                msg = _('Emulator Executable [%s] does not exist' % (emulator_executable))
                self.log_msg('Error: %s' % msg)
                self.message.display_message(
                    _('Error!'),
                    msg,
                    _('Press cancel key to continue...'),
                    wait_for_key=True)
                if self.music_enabled and not game_opts['play_music']:
                    self.gstMusic.play()
                return           
        # Set command line
        if not args:
            args = game_opts['options']
        # Patch for ..[romext]
        if '..' in args:
            newargs = args.split('..')
            args = newargs[0] + '.' + newargs[1]
        cmd = '%s %s' % (emulator_executable, args)
        # Write lock file for emulator
        f = open(self.lock_filename, 'w')
        f.write(cmd)
        f.close()

        if not debug_mode and sys.platform != 'win32':
            self.log_msg('******** Command from Wah!Cade is:  %s ' % cmd)
            # Redirect output to log file
            self.log_msg('******** Begin command output')
            cmd = '%s >> %s 2>&1' % (cmd, self.log_filename)

        # Change to emu dir
        try:
            pwd = os.getcwd()
            os.chdir(os.path.dirname(emulator_executable))
        except:
            pass
        # Run emulator & wait for it to finish
        if not wshell:
            self.p = Popen(cmd, shell=False)
        else:
            self.p = Popen(cmd, shell=True)
        
        # Begins video recording of rom
        if self.options.record:
            self.start_recording_video(rom)
        sts = self.p.wait()
        self.launched_game = True
        # Stops video recording
        if self.options.record:
            self.stop_recording_video()
        self.log_msg("Child Process Returned: " + `sts`, "debug")
        # Minimize wahcade
        if game_opts['minimize_wahcade']:
            self.winMain.iconify()
            self.do_events()
        ### Write to log file
        self.log_msg('******** End command output')
        # Change back to cwd
        os.chdir(pwd)
        # Hide message window
        self.message.hide()  
        self.play_clip('EXIT_GAME')
        self.scrsave_time = time.time()
        # Un-minimize
        if game_opts['minimize_wahcade']:
            self.winMain.present()
            self.do_events()
        # Start timers again
        #self.wait_with_events(0.25)
        self.start_timer('scrsave')
        self.start_timer('video')
        self.start_timer('portal')
        if self.joy is not None:
            self.joy.joy_count('start')
        self.start_timer('joystick')
        if self.music_enabled and not game_opts['play_music']:
            self.gstMusic.play()
        # Stop timing
        time_game_stop = time.time()
        # Add to / update favs list
        if rom not in self.emu_favs_list:
            self.emu_favs_list[rom] = [
                rom,
                self.lsGames[self.listIndex][GL_GAME_NAME],
                0,
                0]
        self.emu_favs_list[rom][FAV_TIMES_PLAYED] += 1
        self.emu_favs_list[rom][FAV_MINS_PLAYED] += int((time_game_stop - time_game_start) / 60)
        # Write favs list to disk, so we don't lose it on unclean exit
        filters.write_fav_list(
            os.path.join(CONFIG_DIR, 'files', '%s.fav' % (self.current_emu)),
            self.emu_favs_list)
        self.do_events()
        self.on_winMain_focus_in()

    def auto_launch_external_app(self, launch_game_after=False, cmdline_args=''):
        """Launch next app in list, then launch game"""
        if launch_game_after:
            self.launch_game_after = True
        if self.external_app_queue:
            self.launch_external_application(self.external_app_queue.pop(), True, cmdline_args)
        elif self.launch_game_after:
            self.launch_game_after = False
            self.launch_game(cmdline_args)

    def launch_external_application(self, app_number, wait_for_finish=False, game_cmdline_args=''):
        """Launch app specified in emu.ini"""
        # Get app name
        app_name = self.emu_ini.get('app_%s_executable' % (app_number))
        app_params = self.emu_ini.get('app_%s_commandline_format' % (app_number))
        # Pre-defined?
        if app_name == 'wahcade-history-viewer':
            if self.histview:
                # Set app number so histview can be closed by same keypress that started it
                self.histview.app_number = app_number
                # Display game history
                self.histview.set_history(
                    self.lsGames[self.listIndex][GL_ROM_NAME],
                    self.lsGames[self.listIndex][GL_GAME_NAME])
            else:
                self.auto_launch_external_app(cmdline_args=game_cmdline_args)
        elif app_name == 'wahcade-cp-viewer':
            if self.cpviewer:
                # Set app number so cpviewer can be closed by same keypress that started it
                self.cpviewer.app_number = app_number
                # Display control panel info
                cpvw_rom = self.lsGames[self.listIndex][GL_ROM_NAME]
                # Use clone name if necessary
                if self.lsGames[self.listIndex][GL_CLONE_OF] != '':
                    cpvw_rom = self.lsGames[self.listIndex][GL_CLONE_OF]
                self.cpviewer.display_game_details(cpvw_rom)
            else:
                self.auto_launch_external_app(cmdline_args=game_cmdline_args)
        else:
            # Get options
            game_opts = self.get_launch_options(app_params)
            # Launch the app
            if os.path.isfile(app_name):
                # Pause music?
                if self.music_enabled and not game_opts['play_music'] and wait_for_finish:
                    self.gstMusic.stop()
                # Minimize wahcade
                if game_opts['minimize_wahcade'] and wait_for_finish:
                    self.winMain.iconify()
                    self.do_events()
                cmd = '%s %s' % (app_name, game_opts['options'])
                self.p = Popen(cmd, shell=True)
                if wait_for_finish:
                    self.p.wait()
                    # Un-minimize
                    if game_opts['minimize_wahcade']:
                        self.winMain.present()
                        self.do_events()
                    # Resume music
                    if self.music_enabled and not game_opts['play_music']:
                        self.gstMusic.play()
            else:
                print _('Error: External Application [%s] does not exist' % (app_name))
            # Call next app
            self.auto_launch_external_app(cmdline_args=game_cmdline_args)

    def load_emulator(self, emulator_name=None):
        """Load emulator"""
        self.launch_game_after = False
        # Stop any vids playing
        self.stop_video()
        # Load emulator ini file
        if emulator_name:
            self.current_emu = emulator_name
            self.wahcade_ini.set('current_emulator', emulator_name)
        # Save current emulator list
        if self.emu_ini:
            self.emu_ini.set('current_list', self.current_list_idx)
            self.emu_ini.write()
        # Load new emulator
        self.emu_ini = MameWahIni(os.path.join(CONFIG_DIR, 'ini', '%s.ini' % (self.current_emu)))
        self.lblEmulatorName.set_text(self.emu_ini.get('emulator_title'))
        self.log_msg('Selected platform: ' + self.emu_ini.get('emulator_title'))
        # Set catver file
        filters._catver_ini = os.path.join(self.emu_ini.get('catver_ini_file'))
        # Calc number of game lists
        file_list = self.build_filelist("", "ini", "(?<=-)\d+", self.current_emu, "-") 
        self.game_lists = []
        self.game_lists_normal = []
        for f in file_list:
            ini = MameWahIni(f)
            # Grab the List number from the current file
            i = self.return_listnum(f)
            # Append lists to both arrays
            self.game_lists.append([ini.get('list_title'), i, ini.getint('cycle_list'), ini.get('list_type')]) 
            self.game_lists_normal.append([ini.get('list_title'), i, ini.getint('cycle_list'), ini.get('list_type')])        

        # Load favorites list
        fav_name = os.path.join(CONFIG_DIR, 'files', '%s.fav' % (self.current_emu))
        if not os.path.isfile(fav_name):
            # Create favorites list if it doesn't exist
            f = codecs.open(fav_name, 'w', 'utf-8-sig')
            f.close()
        self.emu_favs_list = filters.read_fav_list(fav_name)
        # Play videos?
        self.check_video_settings()
        # Load list
        self.current_list_idx = self.emu_ini.getint('current_list')
        self.list_creation_attempted = False
        self.load_list()

    def load_list(self):
        """Load current list"""
        # Load layout for new list
        self.stop_video()
        self.load_layouts(self.layout_orientation)
        # Save last list (if defined)
        if self.current_list_ini:
            self.current_list_ini.write()
        # Load new list
        list_ini_file = os.path.join(CONFIG_DIR, 'ini', '%s-%s.ini' % (self.current_emu, self.current_list_idx))
        if not os.path.isfile(list_ini_file):
            list_ini_file = os.path.join(CONFIG_DIR, 'ini', '%s-0.ini' % (self.current_emu))
            self.current_list_idx = 0
        self.current_list_ini = MameWahIni(list_ini_file)
        self.emu_ini.set('current_list', self.current_list_idx)
        # Load list & set current game
        self.lblGameListIndicator.set_text(self.current_list_ini.get('list_title'))
        self.log_msg('Selected gameslist: ' + self.current_list_ini.get('list_title'))
        # Has initial list file been created?
        game_list_file = os.path.join(
            CONFIG_DIR,
            'files',
            '%s-0.lst' % (self.current_emu))
        if not os.path.isfile(game_list_file):
            self.log_msg('Please Wait. Creating initial filter...')
            self.message.display_message(_('Please Wait'), _('Creating initial filter...'))
            self.list_creation_attempted = True
            self.do_events()
            self.current_list_idx = 0
            filters.create_initial_filter(
                self.emu_ini.get('dat_file'),
                os.path.join(
                    CONFIG_DIR,
                    'files',
                    '%s-0.ftr' % (self.current_emu)),
                game_list_file,
                self.emu_ini)
            self.load_list()
            # Hide message
            self.message.hide()
        # Load the list of games
        self.pop_games_list()
        # Load the list filter
        self.current_filter_changed = False
        if self.current_emu in MAME_INI_FILES:
            filter_file = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-%s.ftr' % (self.current_emu, self.current_list_idx))
            if not os.path.isfile(filter_file):
                # Filter doesn't exist, so try and use use filter for list 0
                filter_file = os.path.join(
                    CONFIG_DIR,
                    'files',
                    '%s-0.ftr' % (self.current_emu))
            self.current_filter = filters.read_filter(filter_file)
        else:
            self.current_filter = None

    def get_layout_filename(self):
        """Returns current layout filename"""
        layout_matched, layout_files = self.get_rotated_layouts(self.layout_orientation)
        if self.layout_orientation != 0 and not layout_matched:
            self.layout_orientation = 0
            layout_matched, layout_files = self.get_rotated_layouts(self.layout_orientation)
        return layout_files[0]

    def load_layout_file(self, layout_file):
        """Load new YAML layout file"""
        # Retrieve filepath to layout file
        layout_path = os.path.join(CONFIG_DIR, 'layouts', self.layout)
        # Store to member variable
        self.layout_path = layout_path
        
        # Layout has not changed, but emulator has. Rebuild visibility for artwork, etc
        if layout_file == self.layout_file:
            self.rebuild_visible_lists()
            return
        
        # Okay to setup
        self.layout_file = layout_file
        layout_info = yaml.load(open(self.layout_file, 'r'))
        
        # Formatting for the high score labels
        hs_data_lay = layout_info['main']['HighScoreData']
        self.highScoreDataMarkupHead = ('<span color="%s" size="%s">' % (hs_data_lay['text-col'], hs_data_lay['font-size']))
        self.highScoreDataMarkupTail = '</span>'
        self.highScoreDataLayout = hs_data_lay
        
        self.scroll_selected_color = layout_info['main']['GameList']['supported-col']
        
        # Formatting for the games overlay letters
        overlay_lay = layout_info['main']['ScrollOverlay']
        self.gamesOverlayMarkupHead = ('<span color="%s" size="%s">' % (overlay_lay['text-col'], overlay_lay['font-size']))
        self.gamesOverlayMarkupTail = '</span>'
        
        # Formatting for the IDs overlay letters
        overlay_lay = layout_info['identify']['ScrollOverlay']
        self.IDsOverlayMarkupHead = ('<span color="%s" size="%s">' % (overlay_lay['text-col'], overlay_lay['font-size']))
        self.IDsOverlayMarkupTail = '</span>'
        
        # Set up main Fixd window
        main = self.winMain
        main_lay = layout_info['main']['fixdMain']
        main.set_size_request(main_lay['width'], main_lay['height'])
        main.set_default_size(main_lay['width'], main_lay['height'])
        main.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(main_lay['background-col']))
        self.fixd.move(self.imgBackground, 0, 0)
        self.imgBackground.set_size_request(main_lay['width'], main_lay['height'])
        main_img = main_lay['use-image']
        # If there is not dirname on the image file (i.e., a relative path was provided)
        # append it to the end of the dirpath to the layouts file
        if not os.path.dirname(main_img):
            main_img = os.path.join(self.layout_path, main_img)
        self.imgBackground.set_data('layout-image', main_img)    
                
        # Set up options Fixd window
        opt = self.options
        opt_lay = layout_info['options']['fixdOpt']
        opt.winOptions.set_size_request(opt_lay['width'], opt_lay['height'])
        opt.winOptions.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(opt_lay['background-col']))
        opt.winOptions.move(opt.imgBackground, 0, 0)
        opt.imgBackground.set_size_request(opt_lay['width'], opt_lay['height'])
        opt_img = opt_lay['use-image']
        # If there is not dirname on the image file (i.e., a relative path was provided)
        # append it to the end of the dirpath to the layouts file
        if not os.path.dirname(opt_img):
            opt_img = os.path.join(self.layout_path, opt_img)
        opt.imgBackground.set_data('layout-image', opt_img)
        self.fixd.move(opt.winOptions,
                       (( main_lay['width'] - opt_lay['width'] ) / 2),
                       (( main_lay['height'] - opt_lay['height'] ) / 2))
        # Other stuff
        opt.lblHeading.set_text(_('Options'))
        opt.lblSettingHeading.set_text(_('Current Setting:'))
        opt.lblSettingValue.set_text('')
        
        # Set up message Fixd window
        msg = self.message
        msg_lay = layout_info['message']['fixdMsg']
        msg.winMessage.set_size_request(msg_lay['width'], msg_lay['height'])
        msg.winMessage.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(msg_lay['background-col']))
        msg.winMessage.move(self.message.imgBackground, 0, 0)
        msg.imgBackground.set_size_request(msg_lay['width'], msg_lay['height'])
        msg_img = msg_lay['use-image']
        self.fixd.move(msg.winMessage,
                       (( main_lay['width'] - msg_lay['width'] ) / 2),
                       (( main_lay['height'] - msg_lay['height'] ) / 2))
        # If there is not dirname on the image file (i.e., a relative path was provided)
        # append it to the end of the dirpath to the layouts file
        if not os.path.dirname(msg_img):
            msg_img = os.path.join(self.layout_path, msg_img)
        msg.imgBackground.set_data('layout-image', msg_img)
        
        # Set up ScreenSaver Fixd window
        scr = self.scrsaver
        self.fixd.move(scr.winScrSaver, 0, 0)
        scr.winScrSaver.set_size_request(main_lay['width'], main_lay['height']) # Match main window
        scr.winScrSaver.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('black'))
        scr.drwVideo.set_size_request(main_lay['width'], main_lay['height'])
        
        # Set up Identify window
        # Match sizes of main window
        idtfy = self.identify
        idtfy_lay = layout_info['identify']['fixdID']
        self.fixd.move(idtfy.winID, 0, 0)
        idtfy.winID.set_size_request(main_lay['width'], main_lay['height'])
        idtfy.winID.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(idtfy_lay['background-col']))
        idtfy.winID.move(idtfy.imgBackground, 0, 0)
        idtfy.imgBackground.set_size_request(main_lay['width'], main_lay['height'])
        idtfy_img = idtfy_lay['use-image']
        if not os.path.dirname(idtfy_img):
            idtfy_img = os.path.join(self.layout_path, idtfy_img)
        idtfy.imgBackground.set_from_file(idtfy_img)
            
        # Set up Player Select window
        plyr = self.player_select
        plyr_lay = layout_info['playerselect']['fixdSelect']
        self.fixd.move(plyr.winPlayers, 0, 0)
        plyr.winPlayers.set_size_request(main_lay['width'], main_lay['height'])
        plyr.winPlayers.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(idtfy_lay['background-col']))
        plyr.winPlayers.move(plyr.imgBackground, 0, 0)
        plyr.imgBackground.set_size_request(main_lay['width'], main_lay['height'])
        plyr_img = plyr_lay['use-image']
        if not os.path.dirname(plyr_img):
            plyr_img = os.path.join(self.layout_path, plyr_img)
        plyr.imgBackground.set_from_file(plyr_img)
        
        # Set up all Widgets
        for w_set_name in self._layout_items.keys():
            wset_layout_info = layout_info[w_set_name]
            for widget, name in self._layout_items[w_set_name]:
                w_lay = wset_layout_info[name]
                # Font
                fontData = w_lay['font']
                if w_lay['font-bold']:
                    fontData += ' Bold'
                fontData += ' %s' % (w_lay['font-size'])
                fontDesc = pango.FontDescription(fontData)
                # Text color
                textColor = w_lay['text-col']
                # Apply
                widget.modify_font(fontDesc)
                widget.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(textColor))
                # BG color, transparency as appropriate
                bgColor = w_lay['background-col']
                parent = widget.get_parent()
                # Check if we have an EventBox ancestor
                if parent.get_ancestor(gtk.EventBox):
                    if w_lay['transparent'] == True:
                        parent.set_visible_window(False)
                    else:
                        parent.set_visible_window(True)
                        parent.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bgColor))
                # Highlight colors (only for scroll lists)
                if type(widget) is ScrollList:
                    widget.modify_highlight_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(w_lay['text-bg-high']))
                    widget.modify_highlight_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(w_lay['text-fg-high']))
                # Alignment of text
                widget.set_property('xalign', w_lay['text-align'])
                # Rotation
                widget.set_data('text-rotation', w_lay['text-rotation'])
                if widget is gtk.Label:
                    widget.set_angle(w_lay['text-rotation'])
                # Visibility
                # Hide self and parents if not visible
                if not w_lay['visible']:
                    widget.hide()
                    if parent.get_ancestor(gtk.EventBox):
                        parent.hide()
                # Show self and parents if visible
                else:
                    widget.show()
                    if parent.get_ancestor(gtk.EventBox):
                        parent.show()
                # Size
                widget.set_size_request(w_lay['width'], w_lay['height'])
                # Scroll overlay stuff
                if 'bg-image' in w_lay:
                    bg_file = self.get_path(w_lay['bg-image'])
                    if not os.path.dirname(bg_file):
                        bg_file = os.path.join(self.layout_path, bg_file)
                    widget.set_from_file(bg_file)
                    widget.hide()
                if 'show-count' in w_lay:
                    widget.charShowCount = w_lay['show-count']
                    widget.hide()
                    
                # Position the video widget
                if self.emu_ini.getint('movie_artwork_no') > 0:
                    self.video_artwork_widget = self._main_images[(self.emu_ini.getint('movie_artwork_no') - 1)]
                    if widget == self.video_artwork_widget:
                        self.fixd.move(self.drwVideo, w_lay['x'], w_lay['y'])
                        self.drwVideo.set_size_request(w_lay['width'], w_lay['height'])
#                # Modify widget reference for lists
#                if widget == self.sclGames:
#                    widget = self.sclGames.fixd
#                elif widget == self.options.sclOptions:
#                    widget = self.options.sclOptions.fixd
#                elif widget == self.identify.sclIDs:
#                    widget = self.identify.sclIDs.fixd
                if isinstance(widget, ScrollList):
                    widget = widget.fixd
                elif parent.get_ancestor(gtk.EventBox):
                    widget = widget.get_parent()
                # Add to fixed layout on correct window
                if w_set_name == "main":
                    # Move widgets to the correct places; move_in_fixd is for the scroll overlay
                    if isinstance(widget, gtk.Widget):
                        self.fixd.move(widget, w_lay['x'], w_lay['y'])
                    else:
                        widget.move_in_fixd(self.fixd, w_lay['x'], w_lay['y'])
                elif w_set_name == "options":
                    self.options.winOptions.move(widget, w_lay['x'], w_lay['y'])
                elif w_set_name == "message":
                    self.message.winMessage.move(widget, w_lay['x'], w_lay['y'])
                elif w_set_name == "screensaver":
                    self.scrsaver.winScrSaver.move(widget, w_lay['x'], w_lay['y'])
                elif w_set_name == "identify":
                    # Move widgets to the correct places; move_in_fixd is for the scroll overlay
                    if isinstance(widget, gtk.Widget):
                        self.identify.winID.move(widget, w_lay['x'], w_lay['y'])
                    else:
                        widget.move_in_fixd(self.identify.winID, w_lay['x'], w_lay['y'])
                elif w_set_name == "playerselect":
                    # Move widgets to the correct places; move_in_fixd is for the scroll overlay
                    if isinstance(widget, gtk.Widget):
                        self.player_select.winPlayers.move(widget, w_lay['x'], w_lay['y'])
                else:
                    print "Orphaned widget detected. Did not belong to one of [main/options/message/screensaver/identify/playerselect]"
        
        # Load histview and cpviewer layouts
        # Still in use?
        self.histview.load_layout(self.histview.layout_filename)
        self.cpviewer.load_layout(self.cpviewer.layout_filename)
        # Build visible lists for displaying artwork images
        self.rebuild_visible_lists()

    def rebuild_visible_lists(self):
        """Get list of visible images & paths"""
        self.visible_img_list = [img for img in self._main_images if img.get_property('visible')]
        self.visible_img_paths = [self.emu_ini.get('artwork_%s_image_path' % (i + 1)) for i, img in enumerate(self.visible_img_list)]
        #self.buildartlist(self.visible_img_paths[0])
        
        # Check background images
        bg_files = (
            [self.imgBackground,
            [os.path.split(os.path.splitext(self.imgBackground.get_data('layout-image'))[0]),
             (self.layout_path, '%s-%s-main.%s' % (self.current_emu, self.current_list_idx, self.layout_orientation)),
             (self.layout_path, '%s-%s-main' % (self.current_emu, self.current_list_idx)),
             (self.layout_path, '%s-main.%s' % (self.current_emu, self.layout_orientation)),
             (self.layout_path, '%s-main' % (self.current_emu)),
             (self.layout_path, 'main.%s' % (self.layout_orientation)),
             (self.layout_path, 'main')]],
            [self.options.imgBackground,
            [os.path.split(os.path.splitext(self.options.imgBackground.get_data('layout-image'))[0]),
             (self.layout_path, '%s-%s-options.%s' % (self.current_emu, self.current_list_idx, self.layout_orientation)),
             (self.layout_path, '%s-%s-options' % (self.current_emu, self.current_list_idx)),
             (self.layout_path, '%s-options.%s' % (self.current_emu, self.layout_orientation)),
             (self.layout_path, '%s-options' % (self.current_emu)),
             (self.layout_path, 'options.%s' % (self.layout_orientation)),
             (self.layout_path, 'options')]],
            [self.message.imgBackground,
            [os.path.split(os.path.splitext(self.message.imgBackground.get_data('layout-image'))[0]),
             (self.layout_path, '%s-%s-message.%s' % (self.current_emu, self.current_list_idx, self.layout_orientation)),
             (self.layout_path, '%s-%s-message' % (self.current_emu, self.current_list_idx)),
             (self.layout_path, '%s-message.%s' % (self.current_emu, self.layout_orientation)),
             (self.layout_path, '%s-message' % (self.current_emu)),
             (self.layout_path, 'message.%s' % (self.layout_orientation)),
             (self.layout_path, 'message')]]
        )
        for img, img_files in bg_files:
            img_filename = self.get_matching_filename(img_files, IMAGE_FILETYPES)
            if os.path.isfile(img_filename):
                img.set_from_file(img_filename)
                img.set_property('visible', True)
            else:
                img.set_property('visible', False)
        # Check logo images
        if self.imgMainLogo.get_property('visible'):
            if self.current_emu in MAME_INI_FILES:
                image_files = []
                for emu in MAME_INI_FILES:
                    image_files.append((self.layout_path, '%s-%s-logo' % (emu, self.current_list_idx)))
                    image_files.append((self.layout_path, '%s-logo' % (emu)))
                    image_files.append((self.layout_path, '%slogo' % (emu)))
                image_files.append((self.layout_path, 'logo'))
            else:
                image_files = [
                    (self.layout_path, '%s-%s-logo' % (self.current_emu, self.current_list_idx)),
                    (self.layout_path, '%s-logo' % (self.current_emu)),
                    (self.layout_path, '%slogo' % (self.current_emu)),
                    (self.layout_path, 'logo')]
            # Get logo filename
            logo_filename = self.get_matching_filename(image_files, IMAGE_FILETYPES)
            if os.path.isfile(logo_filename):
                self.display_scaled_image(self.imgMainLogo, logo_filename, self.keep_aspect, self.imgMainLogo.get_data('text-rotation'))
            else:
                self.imgMainLogo.set_from_file(None)
        # Refresh list (seems necessary for rotated layouts - not sure why at the moment)
        self.on_sclGames_changed()
        self.sclGames.scroll(0)

    def pop_games_list(self):
        """Populate games list"""
        # Which type of list is it?
        if self.current_list_idx == 0 or self.current_list_ini.get('list_type') == 'normal':
            # Normal, so sort list
            list_filename = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-%s.lst' % (self.current_emu, self.current_list_idx))
            if os.path.isfile(list_filename):
                self.lsGames, self.lsGames_len = filters.read_filtered_list(list_filename)
                if self.lsGames_len == 0 and self.current_list_idx == 0 and not(self.list_creation_attempted):
                    #try re-creating list
                    print _('Please Wait. Creating initial filter...')
                    self.message.display_message(_('Please Wait'), _('Creating initial filter...'))
                    self.list_creation_attempted = True
                    self.do_events()
                    self.current_list_idx = 0
                    filters.create_initial_filter(
                        self.emu_ini.get('dat_file'),
                        os.path.join(
                            CONFIG_DIR,
                            'files',
                            '%s-0.ftr' % (self.current_emu)),
                        list_filename,
                        self.emu_ini)
                    self.load_list()
                    # Hide message
                    self.message.hide()
                    return
            else:
                self.lsGames = []
                self.lsGames_len = 0
            self.lsGames.sort()
        elif self.current_list_ini.get('list_type') == 'hi2text_supported':
            # Use all games to gen list
            list_filename = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-0.lst' % (self.current_emu))
            if os.path.isfile(list_filename):
                self.lsGames, self.lsGames_len = filters.read_filtered_list(list_filename)
            else:
                self.lsGames = []
                self.lsGames_len = 0
            # Create list of roms
            flist_roms = [r[GL_ROM_NAME] for r in self.lsGames]
            # Generates hi2text supported list
            hi_2_text_list = []
            for game in self.lsGames:
                if game[GL_ROM_NAME] in self.supported_games:
                    hi_2_text_list.append(game)
            self.lsGames = hi_2_text_list
            self.lsGames_len = len(self.lsGames)
            self.lsGames.sort()
        elif self.current_list_ini.get('list_type') in ['most_played', 'longest_played']:
            # Favs type, so choose sort column
            if self.current_list_ini.get('list_type') == 'most_played':
                sort_column = FAV_TIMES_PLAYED
            else:
                sort_column = FAV_MINS_PLAYED
            # Use all games to gen list
            list_filename = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-0.lst' % (self.current_emu))
            if os.path.isfile(list_filename):
                self.lsGames, self.lsGames_len = filters.read_filtered_list(list_filename)
            else:
                self.lsGames = []
                self.lsGames_len = 0
            # Create list of roms
            flist_roms = [r[GL_ROM_NAME] for r in self.lsGames]
            # Order fav dictionary by number of plays
            favs = list(self.emu_favs_list.values())
            favs.sort(key = itemgetter(sort_column), reverse=True)
            # Order filtered list by favs
            flist_sorted = []
            for fav in favs:
                try:
                    idx = flist_roms.index(fav[FAV_ROM_NAME])
                    flist_sorted.append(self.lsGames[idx])
                except ValueError:
                    self.log_msg("%s not in list" % (fav[FAV_ROM_NAME]))
            self.lsGames = flist_sorted
            self.lsGames_len = len(self.lsGames)
        elif self.current_list_ini.get('list_type') == 'xml_remote' and self.connected_to_server:
            # XML remote-populated, so get the source URL
            sourceURL = self.props['host']+":"+self.props['port']+"/"+self.props['db']+"/game/popular?renderXML=True"
            try:
                data = fromstring(requests.get(sourceURL, headers=self.authorization).text)
            except:
                self.connected_to_server = False
            gList = []
            # Use all games to gen list
            list_filename = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-0.lst' % (self.current_emu))
            if os.path.isfile(list_filename):
                self.lsGames, self.lsGames_len = filters.read_filtered_list(list_filename)
            else:
                self.lsGames = []
                self.lsGames_len = 0
            # Extract data
            if data:
                for game in data.getiterator('game'):
                    try:
                        gList.append(next(gTuple for gTuple in self.lsGames if gTuple[1] == game.find("romName").text))
                    except:
                        pass
            if not gList:
                errorItem = ()
                for i in enumerate(self.lsGames[0]):
                    errorItem += ("No Games Found",) if i==0 else ("",)
                gList.append(errorItem)
            self.lsGames = gList
            self.lsGames_len = len(gList)
        else:
            self.current_list_idx = self.get_next_list_in_cycle(+1)
            self.load_list()
            
        # Setup scroll list
        # "All Games" list is always the first list
        if self.current_list_idx == 0:
            self.sclGames.ls = [l[0] for l in self.lsGames]
        else:
            self.sclGames.ls = []
            for l in [l[0] for l in self.lsGames]:
                # Remove "(bar)" from "foo (bar)" game description
                if len(l) != 0 and l[0] != '(':
                    l = l.split('(')[0]
                self.sclGames.ls.append(l)
        # Select game in list
        current_game = self.current_list_ini.getint('current_game')
        if current_game >= self.lsGames_len:
            current_game = 0
        self.sclGames.set_selected(current_game)
        if not self.init:
            self.on_sclGames_changed()

    def get_random_game_idx(self):
        """Pick a random game index number"""
        return random.randint(0, self.lsGames_len - 1)

    def remove_current_game(self):
        """Remove currently selected game from the list"""
        if len(self.lsGames) != 0:
            self.sclGames.ls.pop(self.sclGames.get_selected())
            self.lsGames.pop(self.sclGames.get_selected())
            filters.write_filtered_list(
                os.path.join(CONFIG_DIR, 'files', '%s-%s.lst' % (
                    self.current_emu, self.current_list_idx)),
                self.lsGames)
            # Update displays
            self.hide_window('options')
            self.sclGames.set_selected(self.sclGames.get_selected() - 1)
            self.sclGames.update()
            

    def check_music_settings(self):
        """If possible, set gstMusic and gstSound"""
        self.gstMusic = None
        self.gstSound = None
        if gst_media_imported:
            try: 
                if self.music_enabled:
                        self.gstMusic = gst_media.MusicPlayer()
                if self.sound_enabled:
                        self.gstSound = gst_media.SoundPlayer()
            except:
                # Playbin object creation failed
                self.log_msg('Warning: Failed to create Music gstreamer objects','0')
                return
            # Check dir
            if not os.path.isdir(self.wahcade_ini.get('music_path')):
                self.log_msg('Error: Music Path [%s] does not exist' % (self.musicpath))
                return
            # Set dir
            tracks = self.gstMusic.set_directory(self.musicpath, MUSIC_FILESPEC)
            # Set volume
            self.gstMusic.set_volume(self.music_vol)
            # Play
            if len(tracks) > 0:
                self.gstMusic.load_playlist(
                    playlist = tracks,
                    play = True,
                    shuffle = self.musicshuffle)

    def check_video_settings(self):
        """If possible, enable video"""
        self.video_enabled = True
        # Did gst_media module import ok?
        if not gst_media_imported:
            self.video_enabled = False
        # Movie delay
        if self.delaymovieprev == 0:
            self.video_enabled = False
        # Check video path exists
        if self.emumovieprevpath != '' and not os.path.exists(self.emumovieprevpath):
            if debug_mode:
                self.log_msg('Error: Movie Preview Path [%s] does not exist' % self.emumovieprevpath,'0')
            self.video_enabled = False
        # Check movie artwork
        if not(self.emumovieartworkno > 0):
            self.video_enabled = False
        # Create gstreamer video player
        if self.video_enabled:
            try:
                self.video_player = gst_media.GstVideo(self.drwVideo)
                self.log_msg('Created Video gstreamer objects','0')
            except:
                # gStreamer object creation failed
                self.video_enabled = False
                self.log_msg('Warning: Failed to create Video gstreamer objects','0')
                return
            
    def on_connection_timer(self):
        #stop the timer if needed
        if self.stop_test_connection_timers:
            return False
        try:
            data = fromstring(requests.get(self.connection_url, headers=self.authorization).text)
        except:
            self.connected_to_server = False
            return False
#        print "Checking for IP Addresses: " + str(len(data.getiterator('connection'))) + " found"
        
        #update the local list of feeds if it has changed
        feeds = [(info.find('ipAddress').text, info.find('port').text) for info in data.getiterator('connection')]
        if self.new_vc_feeds != feeds:
            self.new_vc_feeds = feeds
            self.new_vc_feed_updated = True
        
        #switch to the first remote video that appears and back to the local video when no other videos are left
        for ipAddr in data.getiterator('connection'):
            if not (ipAddr.find('ipAddress').text == self.video_chat.remoteip and ipAddr.find('port').text == self.video_chat.remoteport):
                if len(data.getiterator('connection')) == 1 and ipAddr.find('ipAddress').text == self.video_chat.localip:
                    self.remote_ip = [ipAddr.find('ipAddress').text, ipAddr.find('port').text]
                    self.video_chat.set_remote_info(ipAddr.find('ipAddress').text, ipAddr.find('port').text)
                    was_running = self.video_chat.receiver_running
                    self.stop_video_chat()
                    if was_running:
                        self.start_video_chat()
                    self.manualVCMode = False
                    return True
                elif not self.manualVCMode  and (ipAddr.find('ipAddress').text != self.video_chat.localip or ipAddr.find('port').text != self.video_chat.localport):
                    self.remote_ip = [ipAddr.find('ipAddress').text, ipAddr.find('port').text]
                    if not self.valid_remote_ip(*self.remote_ip):
                        print 'could not connect to', self.remote_ip[0], self.remote_ip[1], '- removing it from server'
                        try:
                            requests.delete(self.connection_url + self.remote_ip[0], headers=self.authorization)
                        except:
                            self.connected_to_server = False
                            return False
                        self.on_connection_timer()
                        return True
                    self.video_chat.set_remote_info(ipAddr.find('ipAddress').text, ipAddr.find('port').text)
                    self.vc_feeds = [(info.find('ipAddress').text, info.find('port').text) for info in data.getiterator('connection')]
                    was_running = self.video_chat.receiver_running
                    self.stop_video_chat()
                    if was_running:
                        self.start_video_chat()
                        return True
                    self.connection_time_running = False
                    return False #Stop the timer if connected
            elif ipAddr.find('ipAddress').text == self.video_chat.remoteip and ipAddr.find('port').text == self.video_chat.remoteport and ipAddr.find('ipAddress').text != self.video_chat.localip and ipAddr.find('port').text != self.video_chat.localport:
                break #if we find the current remote host and it isn't the local video feed, don't change it
        return True 
    
    def on_test_connect_timer(self):
        if self.stop_test_connection_timers:
            return False
        
        found_local = False
        try:
            data = fromstring(requests.get(self.connection_url, headers=self.authorization).text)
        
            for ipAddr in data.getiterator('connection'):
                if ipAddr.find('ipAddress').text == self.video_chat.localip:
                    found_local = True
                    break
            if not found_local:
                print 'couldnt find local ip'
                post_data = {"ipAddress":self.video_chat.localip, "port":self.video_chat.localport}
                requests.post(self.connection_url, post_data, headers=self.authorization)
            return True
        except:
            self.connected_to_server = False
            return False

    def start_timer(self, timer_type):
        """Start given timer"""
        # Screen saver
        if timer_type == 'scrsave' and self.scrsave_delay > 0:
            if self.scrsave_timer:
                gobject.source_remove(self.scrsave_timer)
            self.scrsave_timer = gobject.timeout_add(2500, self.on_scrsave_timer)
        # Video
        elif timer_type == 'video' and self.video_enabled:
            # Stop any playing vids first
            self.stop_video()
            # Restart timer
            self.video_timer = gobject.timeout_add(
                self.delaymovieprev * 1000,
                self.on_video_timer)
        # Joystick
        elif timer_type == 'joystick' and (self.joyint == 1):
            self.joystick_timer = gobject.timeout_add(50, self.joy.poll, self.on_winMain_key_press)
        # Login timer
        elif timer_type == 'login':
            self.timeout = 5; # Number of seconds till recent_log times out
            self.login_timer = gobject.timeout_add(self.timeout * 1000, self.reset_recent_log)
        elif timer_type == 'portal':
            if self.portal_time:
                gobject.source_remove(self.portal_time)
            self.portal_time = gobject.timeout_add(2500, self.portal_timer)
        elif timer_type == 'connection' and not self.connection_time_running:
            self.connection_time = gobject.timeout_add(10000, self.on_connection_timer)
            self.connection_time_running = True
        elif timer_type == 'tstconnect':
            self.test_connection_time = gobject.timeout_add(120000, self.on_test_connect_timer)

    def display_splash(self):
        """Show splash screen"""
        self.splash = gtk.Window()
        self.splash.set_decorated(False)
        self.splash.set_transient_for(self.winMain)
        self.splash.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.splash.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.splash.set_keep_above(True)
        self.splash.set_border_width(self.splash_border_width)
        vbox = gtk.VBox()
        img = gtk.Image()
        self.splash_gfx = os.path.join(CONFIG_DIR, 'layouts', self.layout, 'main-splash.png')
        if os.path.exists(self.splash_gfx):
            self.log_msg('Custom splash found, loading ' + str(self.splash_gfx))
            img.set_from_file(self.splash_gfx)
        else:
            self.splash_gfx = os.path.join(APP_PATH, 'pixmaps', 'Rcade-logo.png')
            self.log_msg('No custom splash found, loading ' + str(self.splash_gfx))
            img.set_from_file(self.splash_gfx)
        if self.splash_show_text == 1:
            lbl = gtk.Label()
            lbl.set_alignment(0.5, 0.5)
            lbl.set_justify(gtk.JUSTIFY_CENTER)
            lbl.set_use_markup(True)
            lbl.set_markup('<big><b>Rcade</b></big>\n%s "%s"' % (VERSION, VERSION_NAME))
            vbox.pack_end(lbl)
        vbox.pack_start(img)
        self.splash.add(vbox)
        self.splash.show_all()
        self.wait_with_events(0.25)

    def get_rotated_layouts(self, angle):
        """Checks for the existence of layout file(s) for given angle.  Returns:
           (main layout filename, history viewer filename, cpviewer filename)
        """
        # Main layout
        layout_path = os.path.join(CONFIG_DIR, 'layouts', self.wahcade_ini.get('layout'))
        layout_extension = ".layy"
        if angle == 0:
            # The 0 degree layout angle _may_ not actually have a angle in the filename as this is the default
            # layout filename so make sure that we include this in the set.
            first_globbed_lay = ''
            glob_lays = glob.glob(os.path.join(layout_path, '*'+layout_extension))
            if len(glob_lays) == 0:
                layout_extension = ".lay"
                glob_lays = glob.glob(os.path.join(layout_path, '*'+layout_extension))
                if len(glob_lays) == 0:
                    print "Failed to find suitable layout file (legacy or current)."
                    exit()
            elif len(glob_lays) > 0:
                first_globbed_lay = glob_lays[0]
            layout_files = [
                (layout_path, '%s-%s.%s' % (self.current_emu, self.current_list_idx, angle)+layout_extension), #0
                (layout_path, '%s-%s' % (self.current_emu, self.current_list_idx)+layout_extension), #1
                (layout_path, '%s.%s' % (self.current_emu, angle)+layout_extension), #2
                (layout_path, '%s.lay' % (self.current_emu)+layout_extension), #3
                (layout_path, 'layout.%s' % (angle)+layout_extension), #4
                (layout_path, 'layout'+layout_extension), #5
                ('', first_globbed_lay), #6
                (os.path.join(CONFIG_DIR, 'layouts', 'classic_640x480'), 'layout.lay')] #7
        else:
            layout_files = [
                (layout_path, '%s-%s.%s' % (self.current_emu, self.current_list_idx, angle)+layout_extension),
                (layout_path, '%s.%s' % (self.current_emu, angle)+layout_extension),
                (layout_path, 'layout.%s' % (angle)+layout_extension)]
        layout_file = self.get_matching_filename(layout_files, '')
        # Check to see whether the returned layout matches the requested orientation
        lfp = [os.path.join(dirname, fp) for dirname, fp in layout_files]
        layout_matched = layout_file in lfp
        # History viewer layout
        hv_layout_path, hv_layout_file = os.path.split(self.histview.histview_ini.get('history_layout'))
        hv_file_base, hv_file_ext = os.path.splitext(hv_layout_file)
        if angle == 0:
            hv_layout_files = [
                (hv_layout_path, '%s.%s%s' % (hv_file_base, angle, hv_file_ext)), #0
                (hv_layout_path, '%s%s' % (hv_file_base, hv_file_ext))] #1
        else:
            hv_layout_files = [
                (hv_layout_path, '%s.%s%s' % (hv_file_base, angle, hv_file_ext))] #0
        hv_layout_file = self.get_matching_filename(hv_layout_files, '')
        # CP viewer layout
        cp_layout_path, cp_layout_file = os.path.split(self.cpviewer.cpviewer_ini.get('viewer_layout'))
        cp_file_base, cp_file_ext = os.path.splitext(cp_layout_file)
        if angle == 0:
            cp_layout_files = [
                (cp_layout_path, '%s.%s%s' % (cp_file_base, angle, cp_file_ext)), #0
                (cp_layout_path, '%s%s' % (cp_file_base, cp_file_ext))] #1
        else:
            cp_layout_files = [
                (cp_layout_path, '%s.%s%s' % (cp_file_base, angle, cp_file_ext))] #0
        cp_layout_file = self.get_matching_filename(cp_layout_files, '')
        # Update ini
        if layout_matched:
            self.wahcade_ini.set('layout_orientation', angle)
            self.wahcade_ini.write()
        # Done
        return layout_matched, [layout_file, hv_layout_file, cp_layout_file]

    def load_layouts(self, requested_angle):
        """Switch layout to specified rotation"""
        # Layout
        if requested_angle == 'toggle':
            # Toggle between 0, 90, 180, 270 degree layouts
            new_angle = (self.layout_orientation + 90) % 360
            layout_matched, layout_files = False, []
            while not layout_matched:
                layout_matched, layout_files = self.get_rotated_layouts(new_angle)
                if not layout_matched:
                    new_angle = (new_angle + 90) % 360
                if new_angle == self.layout_orientation:
                    break
        else:
            # Switch to specified rotation
            new_angle = requested_angle
            layout_matched, layout_files = self.get_rotated_layouts(new_angle)
        # Load rotated layout(s)
        if layout_matched:
            self.layout_orientation = new_angle
            if os.path.isfile(layout_files[0]):
                self.load_layout_file(layout_files[0])
            if os.path.isfile(layout_files[1]):
                self.histview.load_layout(layout_files[1])
            if os.path.isfile(layout_files[2]):
                self.cpviewer.load_layout(layout_files[2])

    def show_window(self, window_name):
        """Show given window"""
        child_win = None
        if window_name == 'message':
            child_win = self.message.winMessage
        elif window_name == 'options':
            child_win = self.options.winOptions
        elif window_name == 'scrsaver':
            child_win = self.scrsaver.winScrSaver
        elif window_name == 'history':
            if self.histview:
                child_win = self.histview.winHistory
        elif window_name == 'cpviewer':
            if self.cpviewer:
                child_win = self.cpviewer.winCPViewer
        elif window_name == 'identify':
            child_win = self.identify.winID
        elif window_name == 'playerselect':
            self.player_select.populate_list()
            child_win = self.player_select.winPlayers
            self.player_select.sclPlayers.set_selected(0)
        # Show given child window
        if child_win:
            self.stop_video()
            child_win.show()
            try:
                child_win.window.raise_()
#                child_win.window.focus() #for bug #382247
            except AttributeError:
                pass
            self.current_window = window_name

    def hide_window(self, window_name='all'):
        """Hide given window"""
        # Hide all child windows
        self.message.winMessage.hide()
        self.options.winOptions.hide()
        self.scrsaver.winScrSaver.hide()
        self.histview.winHistory.hide()
        self.cpviewer.winCPViewer.hide()
        self.identify.winID.hide()
        self.player_select.winPlayers.hide()
        # "show" main
        self.current_window = 'main'
        self.winMain.present()
        if window_name != 'calledfromscreensaver':
            # Start timers again
            self.start_timer('scrsave')
            self.start_timer('portal')
            self.start_timer('video')

    def check_ext_on_game_launch(self, romext='*'):
        """Check that the correct extension is being used"""
        if romext == '' or '*':
            # Lookup Rom Extension for Launch
            roms = glob.glob(os.path.join(self.emu_ini.get('rom_path'), '*'))
            for romname in roms:
                if self.lsGames[self.sclGames.get_selected()][GL_ROM_NAME] in romname:
                    # Set romext to actual extension
                    romext = re.search('\.[^\.]+$',romname).group(0)
                    return romext
        # Multiple Extensions Specified, step through on launch
        elif len(re.search(";",romext).group(0)) > 0:
            m = romext.split(";")
            for romext in m:
                if os.path.isfile(self.emu_ini.get('rom_path') + '/' + self.lsGames[self.sclGames.get_selected()][GL_ROM_NAME] + '.' + romext):
                    return romext

    def check_params(self, check_opts):
        """Check command line options"""
        if check_opts.windowed:
            self.screentype = 0
            self.log_msg("Launching in Windowed Mode")
        if check_opts.fullscreen:
            self.screentype = 1
            self.log_msg("Launching in Fullscreen Mode")
        if check_opts.debug:
            debug_mode = True
            self.log_msg("Debug Mode Enabled")
        if check_opts.disable_gstreamer:
            gst_media_imported = False
            self.log_msg("gstreamer not imported, music/movies/videos playback disabled")
        if check_opts.disable_pygame:
            pygame_imported = False
            self.log_msg("pyGame not imported, joysticks disabled")
        if check_opts.old_keyb_events:
            old_keyb_events = True
            self.log_msg("Old style keyboard events enabled")
    
    def play_clip(self, a_file):
        """Play sound"""
        myclip = os.path.join(CONFIG_DIR, 'layouts', self.wahcade_ini.get('layout'), 'sounds', a_file.lower())
        for ext in MUSIC_FILESPEC_NEW:
            theclip = myclip + "." + ext
            if os.path.exists(theclip) and gst_media_imported and self.sound_enabled:
                self.gstSound.stop()
                self.gstSound.set_volume(self.sound_vol)
                self.gstSound.play(theclip)
            break
        
    def start_recording_video(self, rom):
        """Start recording with RecordMyDesktop"""
        self.wait_with_events(2.00)
        window_name = 'MAME: %s [%s]' % (self.lsGames[self.sclGames.get_selected()][GL_GAME_NAME], rom)
        try:
            os.system('recordmydesktop --full-shots --fps 16 --no-frame --windowid $(xwininfo -name ' + "\'" + str(window_name) + "\'" + ' | awk \'/Window id:/ {print $4}\') -o \'recorded games\'/' + rom + '_highscore &')
        except:
            print "User does not have recordmydesktop installed"

    def stop_recording_video(self):
        """Stop recording by killing RecordMyDesktop"""
        try:
            return os.system('kill `ps -e | awk \'/recordmydesktop/{a=$1}END{print a}\'`')
        except:
            pass

    def run(self):
        """Catches any RFID swipes and sends them to log_in"""
        self.rfid_reader.flushInput()
        while(self.running):
            # Checks if there is an RFID waiting in the output buffer of the arduino
            if self.rfid_reader.inWaiting() >= 12:
#                print "reading card"
                self.scrsave_time = time.time()
                if self.scrsaver.running:
                    self.scrsaver.stop_scrsaver()
                    self.start_timer('scrsave')
                scannedRfid = self.rfid_reader.read(12)
                if len(scannedRfid) == 12 and scannedRfid.isalnum():
                    if self.in_game():
                        self.log_in_queue.put(scannedRfid)
                    elif self.current_window == 'main':
                        self.log_in(scannedRfid)
                else:
                    print "Error during read, please rescan your card"
                self.rfid_reader.flushInput()
            time.sleep(0.125)

    def in_game(self):
        """Check if a game is running"""
        try:
            if self.p.poll() is None:
                return True
            else:
                return False
        except:
            return False
