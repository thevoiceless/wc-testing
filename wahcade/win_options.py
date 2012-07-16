#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
###
# Application: Rcade
# File:        win_options.py
# Description: options window
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
import os
import sys
import string
import fnmatch
#dbus
dbus_imported = False
try:
    import dbus
    dbus_imported = True
except ImportError:
    pass
# GTK
import pygtk
if sys.platform != 'win32':
    pygtk.require('2.0')
import gtk
import gobject
gobject.threads_init()
import pango

# Project modules
from constants import *
from wc_common import WahCade
from scrolled_list import ScrollList
import filters
_ = gettext.gettext


class WinOptions(WahCade):
    """Wah!Cade Options Window"""

    def __init__(self, WinMain):
        # Set main window
        self.WinMain = WinMain
        # Build the window
        self.winOptions = gtk.Fixed()
        self.winOptions.set_has_window(True)
        self.imgBackground = gtk.Image()
        self.lblHeading = gtk.Label()
        self.lblSettingHeading = gtk.Label()
        self.lblSettingValue = gtk.Label()
        self.sclOptions = ScrollList(self.WinMain)
        self.winOptions.add(self.imgBackground)
        self.winOptions.add(self.lblHeading)
        self.winOptions.add(self.lblSettingHeading)
        self.winOptions.add(self.lblSettingValue)
        self.winOptions.add(self.sclOptions.fixd)
        WinMain.fixd.add(self.winOptions)
        self.imgBackground.show()
        self.lblHeading.show()
        self.lblSettingHeading.show()
        self.lblSettingValue.show()
        self.winOptions.show()
        # Build list
        self.lsOptions = []
        self.sclOptions.auto_update = True
        # Get keyboard & mouse events
        self.sclOptions.connect('update', self.on_sclOptions_changed)
        self.sclOptions.connect('mouse-left-click', self.on_sclOptions_changed)
        self.sclOptions.connect('mouse-double-click', self.menu_selected)
        # Setup menu
        self.current_menu = 'main'
        self._menus = {
            'main':
                [[_('Select Platform'), 'emu_list'],
                [_('Select Game List'), 'game_list'],
                [_('Find Game'), 'find'],
                [_('Select Random Game'), 'random'],
                [_('Games List Options'), 'list_options'],
                #['Launch External Application', 'external'],
                [_('Music Options'), 'music'],
                [_('Video Recording Options'), 'record_video'],
                [_('About'), 'about'],
                [_('Exit Wah!Cade'), 'exit']],
                #[_('Close Arcade'), 'shutdown']],
            'list_options':
                [[_('Add Game to List'), 'add_to_list'],
                [_('Remove Game from List'), 'remove_from_list'],
                [_('Generate List...'), 'generate_list']],
            'music':
                [[_('Play / Pause'), 'music_play'],
                [_('Next Track'), 'next_track'],
                [_('Previous Track'), 'previous_track'],
                [_('Select Track / Directory'), 'show_music_dir']],
            'record_video':
                [[_('On'), 'recording_launch'],
                [_('Off'), 'recording_off']],
            'exit':
                [[_('Exit to Desktop'), 'exit_desktop'],
                [_('Exit & Reboot'), 'exit_reboot'],
                [_('Exit & Shutdown'), 'exit_shutdown']],
        }
        self._display_clones = [
            [_('No'), 'no'],
            [_('Yes'), 'yes'],
            [_('Only if better than Parent'), 'better']]
        self._display_clone_idx = 0
        # Init window
        #self.lblHeading.set_ellipsize(pango.ELLIPSIZE_START)
        self.record = False

    def on_sclOptions_changed(self, *args):
        """options menu selected item changed"""
        if self.current_menu == 'generate_ftr':
            # Generate filtered list menu
            if self.sclOptions.get_selected() == 0:
                self.lblSettingValue.set_text(self._display_clones[self._display_clone_idx][0])
            else:
                self.lblSettingValue.set_text('')
        elif self.current_menu.startswith('ftr:'):
            # Filter menu - show yes / no option, etc
            if self.sclOptions.get_selected() < 2:
                # Show all / none
                self.lblSettingValue.set_text('') #With in the setting
            else:
                # Display yes / no
                ftr_section= self.WinMain.current_filter[self.current_menu[4:]]
                item = self.lsOptions[self.sclOptions.get_selected()][0]
                yesno = False
                if item in ftr_section:
                    yesno = ftr_section[item]
                if yesno:
                    self.lblSettingValue.set_text('Yes')
                else:
                    self.lblSettingValue.set_text('No')

    def set_menu(self, menu_level, heading=''):
        """setup options list to given menu"""
        # Get menu heading if not supplied
        if heading == '':
            for v in self._menus.values():
                for ml in v:
                    if ml[1] == menu_level:
                        heading = ml[0]
                        break
        # Default heading
        if heading == '':
            heading = _('Options')
        # Set labels
        self.lblHeading.set_text(heading)
        self.lblSettingHeading.set_text(_('Current Setting:'))
        self.lblSettingValue.set_text('')
        self.lsOptions = []
        # Which menu?
        self.current_menu = menu_level
        # Hide stuff if necessary
        if menu_level == 'main':
            # Hide "select platform" if only one emu in list
            if len(self.WinMain.emu_lists) == 1:
                self._menus[menu_level][0][0] = '**HIDE**'
            # Hide "music" menu
            if not self.WinMain.music_enabled:
                self._menus[menu_level][5][0] = '**HIDE**'
        elif menu_level == 'exit':
            # Hide shutdown & reboot menu
            if not dbus_imported:
                self._menus[menu_level][1][0] = '**HIDE**'
                self._menus[menu_level][2][0] = '**HIDE**'
        # Show menu
        if menu_level == 'emu_list':
            # Show all emulators
            self.lblSettingValue.set_text(self.WinMain.emu_ini.get('emulator_title'))
            for emu_title, emu_name, e in self.WinMain.emu_lists:
                self.lsOptions.append([emu_title, emu_name])
                self.sclOptions.set_selected(0)
        elif menu_level == 'game_list':
            # Show all game lists
            self.lblSettingValue.set_text(self.WinMain.current_list_ini.get('list_title'))
            for list_name, idx, cycle_list, type in self.WinMain.game_lists:
                self.lsOptions.append([list_name, idx]) # The lines selectable, list names
                self.sclOptions.set_selected(self.WinMain.current_list_idx) # Which option is currently highlighted when list is opened
        elif menu_level == 'add_to_list':
            # Show "normal" game lists
            self.lblSettingValue.set_text(self.WinMain.current_list_ini.get('list_title'))
            for list_name, idx, cycle_list, type in self.WinMain.game_lists_normal:
                if list_name != self.WinMain.current_list_ini.get('list_title') and type != 'xml_remote':
                    self.lsOptions.append([list_name, idx])
            self.sclOptions.set_selected(0)
        elif menu_level == 'find':
            # Find by letter
            [self.lsOptions.append([c, 'find:%s' % (c)]) for c in '%s%s' % (string.uppercase, string.digits)]
        elif menu_level == 'list_options':
            # Show game list options menu
            self.sclOptions.set_selected(0)
            if self.WinMain.current_list_idx == 0:
                # List 0, so display "generate list" instead of "generate filtered list"
                self.lsOptions.append(self._menus[menu_level][0])
                self.lsOptions.append(self._menus[menu_level][1])
                self.lsOptions.append(self._menus[menu_level][3])
            else:
                # All other lists
                [self.lsOptions.append(menu_item) for menu_item in self._menus[menu_level][:2]]
        elif menu_level == 'record_video':
            [self.lsOptions.append(menu_item) for menu_item in self._menus[menu_level][:2]] # Generates list choices
            self.sclOptions.set_selected(0) # Sets which option is selected when opened
            if self.record:
                self.lblSettingValue.set_text('On')  # What "Current Setting:" says
            else:
                self.lblSettingValue.set_text('Off')  # What "Current Setting:" says
        elif menu_level == 'generate_list':
            # Re-create initial filter
            self.lblHeading.set_text(_('Please Wait...'))
            self.lblSettingHeading.set_text(_('Generating new games list...'))
            self.do_events()
            filter_file = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-%s.ftr' % (self.WinMain.current_emu, self.WinMain.current_list_idx))
            filters.create_initial_filter(
                self.WinMain.emu_ini.get('dat_file'),
                filter_file,
                os.path.join(
                    CONFIG_DIR,
                    'files',
                    '%s-0.lst' % (self.WinMain.current_emu)),
                self.WinMain.emu_ini)
            self.WinMain.load_list()
            self.WinMain.hide_window('options')
            self.WinMain.sclGames._update_display()
        elif menu_level == 'generate_ftr':
            # Display filter categories menu
            self._display_clone_idx = int(self.WinMain.current_filter['filter_type'])
            self.sclOptions.set_selected(0)
            [self.lsOptions.append(menu_item) for menu_item in self._menus[menu_level]]
        elif menu_level.startswith('ftr:'):
            # Display a specific filter menu...
            self.sclOptions.set_selected(0)
            # Get title
            for mdesc, mcode in self._menus['generate_ftr']:
                if mcode == menu_level:
                    title = mdesc
                    break
            self.lblHeading.set_text(title)
            # Display all items in filter
            for filt_item in self.WinMain.current_filter[menu_level[4:]].keys():
                self.lsOptions.append([filt_item, filt_item])
            self.lsOptions.sort()
            self.lsOptions.insert(0, [_('Show ALL'), 'all'])
            self.lsOptions.insert(1, [_('Show NONE'), 'none'])
        elif menu_level == 'generate_new_list':
            # Generate new filtered games list
            self.lblHeading.set_text(_('Please Wait...'))
            self.lblSettingHeading.set_text(_('Generating new filtered games list...'))
            self.do_events()
            # Save current filter
            filters.write_filter(
                self.WinMain.current_filter,
                os.path.join(
                    CONFIG_DIR,
                    'files',
                    '%s-%s.ftr' % (self.WinMain.current_emu, self.WinMain.current_list_idx)))
            # Create list from the just saved filter
            filters.create_filtered_list(
                os.path.join(
                    CONFIG_DIR,
                    'files',
                    '%s-0.lst' % (self.WinMain.current_emu)),
                self.WinMain.current_filter,
                os.path.join(
                    CONFIG_DIR,
                    'files',
                    '%s-%s.lst' % (self.WinMain.current_emu, self.WinMain.current_list_idx)))
            self.WinMain.load_list()
            self.WinMain.hide_window('options')
        elif menu_level == 'music_dir':
            # Display contents of current music dir
            #print "music dir=", self.WinMain.gstMusic.current_dir
            self.lblHeading.set_text(self.WinMain.gstMusic.current_dir)
            dir_files, music_files = self.get_music_files(self.WinMain.gstMusic.current_dir)
            self.sclOptions.set_selected(0)
            for df in dir_files:
                self.lsOptions.append([df, 'music_dir'])
            for mf in music_files:
                self.lsOptions.append([mf, 'music_track'])
        else:
            # Show appropriate menu
            self.sclOptions.set_selected(0)
            #[self.lsOptions.append(menu_item) for menu_item in self._menus[menu_level]]
            [self.lsOptions.append(m) for m in self._menus[menu_level] if m[0] != '**HIDE**']
        # Update list widget
        self.sclOptions.ls = [l[0] for l in self.lsOptions]
        self.sclOptions.set_selected(self.sclOptions.get_selected())

    def menu_selected(self, *args):
        """menu item selected"""
        if len(self.lsOptions) <= 0:
            # No options!
            return
        # Get selected item
        menu_desc, menu_item = self.lsOptions[self.sclOptions.get_selected()]
        if self.current_menu == 'main':
            # Main menu
            if menu_item == 'random':
                # Pick random game
                self.WinMain.sclGames.set_selected(self.WinMain.get_random_game_idx())
                self.WinMain.sclGames.update()
            elif menu_item == 'about':
                # About
                self.show_about_dialog('Rcade', CONFIG_DIR)
                self.WinMain.hide_window('options')
            else:
                # Show appropriate menu
                self.set_menu(menu_item, menu_desc)
        elif self.current_menu == 'record_video':
            if menu_item == 'recording_launch':
                self.record = True
                self.lblSettingValue.set_text('On')  # What "Current Setting:" says
            elif menu_item == 'recording_off':
                self.record = False
                self.lblSettingValue.set_text('Off')  # What "Current Setting:" says
        elif self.current_menu == 'emu_list':
            # Emulator list menu, so switch to selected emulator
            self.WinMain.hide_window('options')
            self.WinMain.load_emulator(menu_item)
        elif self.current_menu == 'game_list':
            # Game list menu, so switch to selected list
            self.WinMain.hide_window('options')
            self.WinMain.current_list_idx = int(menu_item)
            self.WinMain.load_list()
        elif self.current_menu == 'list_options':
            # Games list options menu
            if menu_item == 'remove_from_list':
                # Remove current game from current list
                self.WinMain.remove_current_game()
            else:
                # Show menu
                self.set_menu(menu_item, menu_desc)
        elif self.current_menu == 'add_to_list':
            # Check game isn't already on list
            new_list_filename = os.path.join(
                CONFIG_DIR,
                'files',
                '%s-%s.lst' % (self.WinMain.current_emu, int(menu_item)))
            selected_game = self.WinMain.lsGames[self.WinMain.sclGames.get_selected()]
            new_list = filters.read_filtered_list(new_list_filename)
            if selected_game not in new_list:
                # Add current selected game to chosen game list
                filters.add_game_to_filtered_list(
                    gd = filters.get_game_dict(selected_game),
                    list_filename = new_list_filename)
            self.WinMain.hide_window('options')
        elif self.current_menu == 'generate_ftr':
            # Filtered lists
            if menu_item == 'ftr:filter_type':
                # Change filter type (display clones)
                self._display_clone_idx += 1
                if self._display_clone_idx > 2:
                    self._display_clone_idx = 0
                self.on_sclOptions_changed()
                self.WinMain.current_filter_changed = True
                self.WinMain.current_filter['filter_type'] = self._display_clone_idx
            else:
                # Show filter... menu
                self.set_menu(menu_item, menu_desc)
        elif self.current_menu.startswith('ftr:'):
            # Update current filter
            self.WinMain.current_filter_changed = True
            ftr_section = self.WinMain.current_filter[self.current_menu[4:]]
            if self.sclOptions.get_selected() == 0:
                # Set all = yes
                for k in ftr_section.keys():
                    ftr_section[k] = True
            elif self.sclOptions.get_selected() == 1:
                # Set all = no
                for k in ftr_section.keys():
                    ftr_section[k] = False
            else:
                # Set yes / no
                item = self.lsOptions[self.sclOptions.get_selected()][0]
                yesno = (self.lblSettingValue.get_text().lower() == 'yes')
                ftr_section[item] = not yesno
                self.on_sclOptions_changed()
        elif self.current_menu == 'find':
            # Find by letter
            self.find_game('add', menu_item[5:])
        elif self.current_menu == 'music':
            if menu_item == 'music_play':
                # Play / pause
                #print "music_play"
                self.WinMain.gstMusic.play_toggle()
            elif menu_item == 'next_track':
                self.WinMain.gstMusic.next_track()
            elif menu_item == 'previous_track':
                self.WinMain.gstMusic.previous_track()
            elif menu_item == 'show_music_dir':
                # Select music dir
                self.set_menu('music_dir')
        elif self.current_menu == 'music_dir':
            # Select music dir
            if menu_item == 'music_dir':
                # Dir selected
                if menu_desc == '..':
                    # Go to parent dir
                    new_music_dir = os.path.dirname(self.WinMain.gstMusic.current_dir)
                else:
                    # Change to selected dir
                    new_music_dir = os.path.join(self.WinMain.gstMusic.current_dir, menu_desc)
                # Load dir & play
                tracks = self.WinMain.gstMusic.set_directory(new_music_dir, MUSIC_FILESPEC)
                if len(tracks) > 0:
                    self.WinMain.gstMusic.load_playlist(
                        playlist = tracks,
                        play = True,
                        shuffle = self.WinMain.wahcade_ini.get('shuffle_music', 0))
                # Display music menu
                self.set_menu('music_dir')
            elif menu_item == 'music_track':
                # Track selected
                new_track = os.path.join(self.WinMain.gstMusic.current_dir, menu_desc)
                #print "self.WinMain.gstMusic.tracks=",self.WinMain.gstMusic.tracks
                idx = self.WinMain.gstMusic.tracks.index(new_track)
                self.WinMain.gstMusic.current_track = idx - 1
                self.WinMain.gstMusic.next_track()
        elif self.current_menu == 'exit':
            if menu_item == 'exit_desktop':
                self.WinMain.exit_wahcade()
            elif menu_item == 'exit_reboot':
                self.WinMain.exit_wahcade('reboot')
            elif menu_item == 'exit_shutdown':
                self.WinMain.exit_wahcade('shutdown')
        else:
            # Unhandled menu item
            print "unhandled menu"
            print "  self.current_menu=", self.current_menu
            print "  menu_item=", menu_item

    def find_game(self, cmd, new_letter=None):
        """either add or delete a letter or go back to main menu"""
        if cmd == 'add':
            # Add a letter
            self.lblSettingValue.set_text('%s%s' % (self.lblSettingValue.get_text(), new_letter))
            # Find game in list beginning with entered letters
            for idx, game_name in enumerate(self.WinMain.sclGames.ls):
                if game_name.upper().startswith(self.lblSettingValue.get_text()):
                    self.WinMain.sclGames.set_selected(idx)
                    self.WinMain.sclGames.update()
                    break
        elif cmd == 'back':
            if self.lblSettingValue.get_text() == '':
                # Go back to main menu
                self.set_menu('main')
            else:
                # Remove a letter
                self.lblSettingValue.set_text(self.lblSettingValue.get_text()[:-1])

    def get_music_files(self, music_path):
        """return list of dirs and files matching spec from path"""
        # Get all files in given path
        all_files = os.listdir(music_path)
        # Get music files
        music_files = []
        for filespec in MUSIC_FILESPEC.split(';'):
            mf = fnmatch.filter(all_files, filespec)
            for f in mf:
                music_files.append(f)
        music_files.sort(key=str.lower)
        # Remove music files from list
        remaining_files = [f for f in all_files if f not in music_files and not f.startswith('.')]
        # Test each remaining file to see if it's a dir
        dir_files = [f for f in remaining_files if os.path.isdir(os.path.join(music_path, f))]
        dir_files.sort(key=str.lower)
        dir_files.insert(0, '..')
        # Done
        return dir_files, music_files
