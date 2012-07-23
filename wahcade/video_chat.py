#!/usr/bin/env python
'''
Created on Jul 12, 2012

@author: dwilson
'''

import os
import pygst
pygst.require("0.10")
import gst
import commands
from constants import CONFIG_DIR
import requests
import socket
import gtk
import pygame

class video_chat():
    
    def __init__(self, WinMain):
        self.WinMain = WinMain
        self.enabled = True
        self.receiver_running = False
        
        self.receivepipe = None

        self.video_width, self.video_height = 320, 240
        #self.localip, self.localport = self.WinMain.local_IP, str(self.get_open_port())
        self.localip, self.localport = str(self.get_local_ip()), str(self.get_open_port())
        #print self.localip + " " + self.localport 
        self.remoteip, self.remoteport = "", "" #self.localip, self.localport #do a video loopback initially
        
        self.enabled = self.camera_available()
        
    
    def setup_video_streamer(self):
        #webm video pipeline, optimized for video conferencing
        device = self.get_camera_name()
        #videosrc = "v4l2src device=" + device #specify a specific camera
        videoSrc = "autovideosrc" #auto detect the source
        #videoSrc = "videotestsrc" #test source
        #v4l2src device=" + device + "
        command = videoSrc + " ! video/x-raw-rgb, width=" + str(self.video_width) + ", height=" + str(self.video_height) + " "
        command += "! ffmpegcolorspace ! vp8enc speed=2 max-latency=2 quality=10.0 max-keyframe-distance=3 threads=5 " 
        command += "! queue2 ! mux. autoaudiosrc ! audioconvert ! vorbisenc " 
        command += "! queue2 ! mux. webmmux name=mux streamable=true "
        command += "! tcpserversink host=" + self.localip + " port=" + self.localport
        
        self.streampipe = gst.parse_launch(command)
        self.streampipe.set_state(gst.STATE_PLAYING) #start the video stream
        bus = self.streampipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_stream_message)

        print "Streaming video on " + self.localip + ":" + self.localport
    
    def setup_video_receiver(self):
        #webm encoded video receiver
        #self.remoteip, self.remoteport = "127.0.0.1", self.localport #COMMENT THIS TO ALLOW MULTIPLE MACHINES
        try:
            import urllib2
            urllib2.urlopen('http://' + self.remoteip, timeout=1)
        except urllib2.URLError:
            print 'could not connect to', self.remoteip, self.remoteport, 'removing it from server'
            requests.delete(self.WinMain.connection_url + self.remoteip)
            self.WinMain.start_timer('connection')
            self.remoteip, self.remoteport = "", ""
            del self.WinMain.remote_ip[:]
            self.WinMain.on_connection_timer()
            return 0
            
        command = "tcpclientsrc host=" + self.remoteip + " port=" + self.remoteport + " " 
        command += "! matroskademux name=d d. ! queue2 ! vp8dec ! ffmpegcolorspace ! xvimagesink name=sink sync=false " 
        command += "d. ! queue2 ! vorbisdec ! audioconvert ! audioresample ! alsasink sync=false"
        self.receivepipe = gst.parse_launch(command) 
        #self.receivepipe.set_state(gst.STATE_PLAYING)
        self.sink = self.receivepipe.get_by_name("sink")
        bus = self.receivepipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)
        self.receiver_running = True
        print 'receiver running on', self.remoteip, self.remoteport
        return 1
        
#        self.receivepipe.set_state(gst.STATE_PLAYING)
        
        #print "Video Chat Receiver started"
        
    def receiver_ready(self):
        if not self.receivepipe:
            return False
        return True
            
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80)) #connect to Google's DNS server
        #self.local_IP = s.getsockname()[0] #Get local ip address
        localip = s.getsockname()[0]
        s.close()
        return localip
    
    def get_open_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port
    
    def camera_available(self):
        camNames = commands.getoutput("dir -format -1 /dev | grep 'video*'").strip()
        if len(camNames) == 0:
            return False
        else:
            return True
    
    def get_camera_name(self, index = 0):
        #Get the first camera's device number
        listOfCameras = commands.getoutput("dir -format -1 /dev | grep 'video*'").strip().split("\n")
        camCount = len(listOfCameras)
        device = ""
        if self.camera_available():
            if camCount == 1: 
                print "There is 1 camera: " + ", ".join(listOfCameras)
            else:
                print "There are", camCount, "cameras: " + ", ".join(listOfCameras)
            device = "/dev/" + listOfCameras[index]
        
        return device
    
    def change_remote_ip(self, ip, port):
        #was_running = True 
        was_running = self.receiver_running
        self.remoteip = ip
        self.remoteport = port
        self.stop_receiver()
        self.setup_video_receiver()
        if was_running:
            self.start_receiver()
    
    def video_is_streaming(self):
        if self.streampipe and self.streampipe.get_state()[1] == gst.STATE_PLAYING:
            return True
        return False
    
    def start_streaming_video(self):
        if self.streampipe and not self.video_is_streaming(): 
            self.streampipe.set_state(gst.STATE_PLAYING)
    
    def stop_streamer(self):
        if self.streampipe:
            self.streampipe.set_state(gst.STATE_NULL)
    
    def start_receiver(self):
        if self.receivepipe:
            self.receivepipe.set_state(gst.STATE_PLAYING)
            #self.receiver_running = True
            
    def stop_receiver(self):
        if self.receivepipe:
            self.receivepipe.set_state(gst.STATE_NULL)
            self.receiver_running = False

    def kill_pipelines(self):
        if self.receivepipe:
            self.stop_receiver()
        if self.streampipe:
            self.stop_streamer()
    
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            was_running = self.receiver_running
            self.receiver_running = False
            self.stop_receiver()
            if was_running:
                self.WinMain.start_video_chat()
            #self.kill_pipelines()
        elif t == gst.MESSAGE_ERROR:
            self.receiver_running = False
            err, debug = message.parse_error()
            print "Receiver Error: %s" % self.remoteip, self.remoteport, err, debug
            #self.kill_pipelines()
            self.stop_receiver()
        elif t == gst.MESSAGE_STATE_CHANGED:
            #print 'Message: ' + str(message)
            old, new, pending = message.parse_state_changed()
            #print "Receiver State: " + str(new)
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return False
        name = message.structure.get_name()
        if name == "prepare-xwindow-id":
            gtk.gdk.threads_enter()
            gtk.gdk.display_get_default().sync()
            
            videooutput = message.src
            videooutput.set_property("force-aspect-ratio", True)
            self.WinMain.vc_box.show()
            if self.WinMain.vc_box and self.WinMain.vc_box.window:
                videooutput.set_xwindow_id(self.WinMain.vc_box.window.xid)
            else:
                print "Video Chat Error: Unable to link the video source to the receiver sink."
            gtk.gdk.threads_leave()
    
    def on_stream_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Stream Error: %s" % err, debug
            #self.kill_pipelines()
            self.stop_streamer()
        elif t == gst.MESSAGE_STATE_CHANGED:
            #print 'Stream Message: ' + str(message)
            old, new, pending = message.parse_state_changed()
            #print "Stream State: " + str(new)

#Creates a stand alone version of video chat
class standalone_player():
    def __init__(self):
        self.vc = video_chat(self)
        
        self.vc.remoteip = self.vc.localip
        self.vc.remoteport = self.vc.localport
        
        window = gtk.Window()
        window.set_title('Video Chat Test')
        #window.set_default_size(640, 480)
        window.connect("destroy", gtk.main_quit, "WM destroy")
        
        fixed = gtk.Fixed()
        vbox = gtk.VBox()
        self.vc_box = gtk.DrawingArea()
        self.vc_box.set_size_request(self.vc.video_width,self.vc.video_height)
        startStreamButton = gtk.Button("Start Streaming")
        startStreamButton.connect("clicked", self.OnStreamStart)
        stopStreamButton = gtk.Button("Stop Streaming")
        stopStreamButton.connect("clicked", self.OnStreamStop)
        
        startReceiveButton = gtk.Button("Start Receiving")
        startReceiveButton.connect("clicked", self.OnReceiveStart)
        stopReceiveButton = gtk.Button("Stop Receiving")
        stopReceiveButton.connect("clicked", self.OnReceiveStop)
        
        buttonBox = gtk.HButtonBox()
        buttonBox.add(startStreamButton)
        buttonBox.add(stopStreamButton)
        buttonBox.add(startReceiveButton)
        buttonBox.add(stopReceiveButton)
        
        vbox.pack_start(self.vc_box)
        
        vbox.pack_start(buttonBox)
        fixed.put(vbox, 0, 0)
        window.add(fixed)
        
        window.show_all()
        
        print self.vc.camera_available()
    
    def OnStreamStart(self, widget):
        self.vc.setup_video_streamer()
    def OnStreamStop(self, widget):
        self.vc.stop_streamer()
    
    def OnReceiveStart(self, widget):
        self.vc.setup_video_receiver()
        self.vc.start_receiver()
    def OnReceiveStop(self, widget):
        self.vc.stop_receiver()
    
if __name__ == "__main__":
    standalone_player()
    gtk.gdk.threads_init()
    gtk.main()
