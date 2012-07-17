#!/usr/bin/env python
'''
Created on Jul 12, 2012

@author: dwilson
'''

import sys, os
import gobject, pygst
pygst.require("0.10")
import gst
import commands
import threading
from constants import *
import requests

class video_chat():
    
    def __init__(self, WinMain):
        self.WinMain = WinMain
        self.enabled = True
        self.vc_file = CONFIG_DIR + "/confs/VC-default.txt"
        try:
            if os.path.exists(self.vc_file):
                with open(self.vc_file, 'rt') as f: # Open the config file and extract the video config info
                    self.props = {}  # Dictionary
                    for line in f.readlines():
                        val = line.split('=')
                        self.props[val[0].strip()] = val[1].strip()  # Match each key with its value
                    
                    self.video_width, self.video_height = int(self.props["width"]), int(self.props["height"])
                    self.localip, self.localport = self.WinMain.local_IP, self.props['localport']
                    self.remoteip, self.remoteport = self.WinMain.local_IP, self.props["remoteport"]
                    
                    if self.localip != "" or self.localip != None:
                        post_data = {"ipAddress":self.localip, "port":self.localport}
                        r = requests.post(self.WinMain.connection_url, post_data)
            else:
                print "The video chat configuration file was not found at: " + self.vc_file
                self.enabled = False
                return 

        except: 
            print "There was an error loading the video chat configuration."
            self.enabled = False
            return

        
        #Set up the streaming pipelines
        self.setup_streaming_video()
        self.start_video_receiver()
        #raw_input("Press Enter to start streaming your video camera")
        
    def start_video_receiver(self):
        #webm encoded video receiver
        command = "tcpclientsrc host=" + self.localip + " port=" + self.localport + " " 
        command += "! matroskademux name=d d. ! queue2 ! vp8dec ! ffmpegcolorspace ! xvimagesink name=sink sync=false " 
        command += "d. ! queue2 ! vorbisdec ! audioconvert ! audioresample ! alsasink sync=false"
        self.receivepipe = gst.parse_launch(command) 
        #self.receivepipe.set_state(gst.STATE_PLAYING)
        
        self.sink = self.receivepipe.get_by_name("sink")
        bus = self.receivepipe.get_bus()
        bus.add_signal_watch()
#        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
#        bus.connect("sync-message::element", self.on_sync_message)
        
#        self.receivepipe.set_state(gst.STATE_PLAYING)
        print "Video Chat Receiver started"
        
    def get_camera_name(self, index = 0):
        #Get the first camera's device number
        listOfCameras = commands.getoutput("dir -format -1 /dev | grep 'video*'").split("\n")
        camCount = str(len(listOfCameras))
        device = ""
        if camCount == 0:
            print "No cameras were detected.  You can't stream video, but you can receive it."
        else:
            if int(camCount) == 1: 
                print "There is 1 camera: " + ", ".join(listOfCameras)
            else:
                print "There are", camCount, "cameras: " + ", ".join(listOfCameras)
            device = "/dev/" + listOfCameras[index]
        
        return device
    
    def video_is_streaming(self):
        if self.streampipe.get_state()[1] == gst.STATE_PLAYING:
            return True
        return False
    
    def setup_streaming_video(self):
        #webm video pipeline, optimized for video conferencing
        device = self.get_camera_name()
        command = "v4l2src device=" + device + " ! video/x-raw-rgb, width=" + str(self.video_width) + ", height=" + str(self.video_height) + " "
        command += "! ffmpegcolorspace ! vp8enc speed=2 max-latency=2 quality=10.0 max-keyframe-distance=3 threads=5 " 
        command += "! queue2 ! mux. alsasrc device=plughw:1,0 ! audioconvert ! vorbisenc " 
        command += "! queue2 ! mux. webmmux name=mux streamable=true "
        command += "! tcpserversink host=" + self.remoteip + " port=" + self.remoteport
        
        self.streampipe = gst.parse_launch(command)
        self.streampipe.set_state(gst.STATE_PLAYING)
        bus = self.streampipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_stream_message)
    
    def start_streaming_video(self):
        if not self.video_is_streaming(): 
            self.streampipe.set_state(gst.STATE_PLAYING)
    
    def pause_streaming_video(self):
        self.streampipe.set_state(gst.STATE_PAUSED)
    
    
    
    def stop_receiver(self):
        self.receivepipe.set_state(gst.STATE_PAUSED)
        
    def start_receiver(self):
        self.receivepipe.set_state(gst.STATE_PLAYING)
    
    def kill_pipelines(self):
        self.receivepipe.set_state(gst.STATE_NULL)
        self.streampipe.set_state(gst.STATE_NULL)
    
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.kill_pipelines()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.kill_pipelines()
        elif t == gst.MESSAGE_STATE_CHANGED:
            #print 'Message: ' + str(message)
            old, new, pending = message.parse_state_changed()
            #print "State: " + str(new)
            if new == gst.STATE_NULL:
                print 'stopped'
    
    def on_stream_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Stream Error: %s" % err, debug
            self.stop_streaming_video()
        elif t == gst.MESSAGE_STATE_CHANGED:
            #print 'Stream Message: ' + str(message)
            old, new, pending = message.parse_state_changed()
            #print "Stream State: " + str(new)
