#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
###
# Application: Rcade
# File:        load_LDAP.py
# Description: Connects to and loads from an Active Directory or LDAP server
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

import os
import ldap
from ldap.controls import SimplePagedResultsControl
from constants import *

class LoadLDAP:
    """Connects to a given LDAP server"""
    
    def __init__(self):
        self.OUTPUT_TO_FILE = False
        self.LDAP_connected = False
        self.updateLDAP()
        
    def updateLDAP(self):
        self.loadCreds()
        self.fetchNames()
        self.generateLists()
    
    def loadCreds(self):
        # Load LDAP credentials from local file
#        self.LDAP_file = str(os.environ['HOME']) + "/Documents/LDAP.txt"
        self.LDAP_file = CONFIG_DIR + "/confs/LDAP.txt" if os.path.isfile(CONFIG_DIR + "/confs/LDAP.txt") else CONFIG_DIR + "/confs/LDAP-default.txt"
        try:
            with open(self.LDAP_file, "rt") as f:
                self.creds = {}
                for line in f.readlines():
                    val = line.split('|')   # This file uses "|" instead of "="
                    self.creds[val[0].strip()] = val[1].strip()
        except:
            print "Could not load LDAP configuration file."
            
        self.LDAP_SERVER = self.creds['LDAP_SERVER']
        self.BIND_DN = self.creds['BIND_DN']
        self.BIND_PASS = self.creds['BIND_PASS']
        self.USER_BASE = self.creds['USER_BASE']
        self.USER_FILTER = self.creds['USER_FILTER']
        self.PAGE_SIZE = int(self.creds['PAGE_SIZE'])
    
    def fetchNames(self):
        try:
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, 0)
            self.ldap_connection = ldap.initialize(self.LDAP_SERVER)
            self.ldap_connection.simple_bind_s(self.BIND_DN, self.BIND_PASS)
            print "Successfully connected to", str(self.creds['LDAP_SERVER'])
            self.LDAP_connected = True
        except ldap.LDAPError, e:
            print "Failed to connect to LDAP server: " + str(e)
            self.LDAP_connected = False
        
        self.accounts = []
        self.pages = 0
        if self.LDAP_connected:
            # Look up usernames via paged search
            self.paged_results_control = SimplePagedResultsControl(ldap.LDAP_CONTROL_PAGE_OID, True, (self.PAGE_SIZE, ''))
            while True:
                self.serverctrls = [self.paged_results_control]
                try:
                    self.msgid = self.ldap_connection.search_ext(self.USER_BASE,
                                                       ldap.SCOPE_SUBTREE,
                                                       self.USER_FILTER,
                                                       attrlist = ['cn', 'sAMAccountName'],
                                                       serverctrls = self.serverctrls)
                except ldap.LDAPError, e:
                    print "Error performing paged search: " + str(e)
                    
                #print "msgid:", msgid
                
                try:
                    unused_code, self.results, unused_msgid, self.serverctrls = self.ldap_connection.result3(self.msgid)
                except ldap.LDAPError, e:
                    print "Error getting user paged search results: " + str(e)
                    
                #print "unused_code:", unused_code
                #print "results:", results
                #print results
                #print "unused_msgid:", unused_msgid
                
                for result in self.results:
                    self.pages += 1
                    self.accounts.append(result)
                
                self.cookie = None
                for serverctrl in self.serverctrls:
                    if serverctrl.controlType == ldap.LDAP_CONTROL_PAGE_OID:
                        unused_est, self.cookie = serverctrl.controlValue
                        if self.cookie:
                            self.paged_results_control.controlValue = (self.PAGE_SIZE, self.cookie)
                        break
                if not self.cookie:
                    break
            
            # Unbind
            self.ldap_connection.unbind_s()
    
    def generateLists(self):
        # Dictionary with user data
        self.user_map = {}
        # List of real names
        self.user_names = []
        for entry in self.accounts:
            #print entry
            #print entry[1]
            if entry[1].has_key('cn') and entry[1].has_key('sAMAccountName'):
                self.user_map[entry[1]['cn'][0]] = entry[1]['sAMAccountName'][0]
                self.user_names.append(entry[1]['cn'][0])
                
    def writeToFile(self):
        if self.OUTPUT_TO_FILE:
            with open("readytalk-users.txt", "w") as f:
                for name in self.user_names:
                    f.write(name + '\n')
                    
    def getMap(self):
        return self.user_map
    
    def getNames(self):
        return self.user_names
    
