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
import gtk

class video_chat:
    
    def __init__(self):
        self.video_width, self.video_height = 640, 480

        self.localip, self.localport = "192.168.50.183", "3000"
        self.remoteip, self.remoteport = "192.168.50.183", "3000"
        
        #Set up the streaming pipelines
        self.start_video_receiver()
        #raw_input("Press Enter to start streaming your video camera")
        self.setup_streaming_video()
        
    def start_video_receiver(self):
        #Video Receiver
        #webm encoding receiver
        self.receivepipe = gst.parse_launch("tcpserversrc host=" + self.localip + " port=" + self.localport + " ! matroskademux name=d d. ! queue2 ! vp8dec ! ffmpegcolorspace ! xvimagesink name=sink d. ! queue2 ! vorbisdec ! audioconvert ! audioresample ! alsasink sync=false") 
        
        #jpeg encoding receiver
        #receivepipe2 = gst.parse_launch("tcpserversrc host=" + self.localip + " port=" + self.localport + " ! decodebin2 name=dec ! audioconvert ! alsasink dec. ! xvimagesink")
        #receivepipe2.set_state(gst.STATE_PLAYING)
        
        self.receivepipe.set_state(gst.STATE_PLAYING)
        print "Receiver started"
        
    def get_camera_name(self, index = 0):
        #Get the first camera's device number
        listOfCameras = commands.getoutput("dir -format -1 /dev | grep 'video*'").split("\n")
        camCount = str(len(listOfCameras))
        device = ""
        if camCount == 0:
            print "No cameras were detected.  You can't stream video, but you can receive it."
        else:
            if camCount == 1: 
                print "There is " + str(camCount) + " cameras (" + listOfCameras + ")"
            else:
                print "There are " + str(camCount) + " camera(s)"
            device = "/dev/" + listOfCameras[index]
        
        return device
    
    def video_is_streaming(self):
        if self.streampipe.get_state() == gst.STATE_PLAYING:
            return True
        return False
    
    def setup_streaming_video(self):
        device = self.get_camera_name()
        
        #Video streamer
        #webm video pipeline, optimized for video conferencing
        self.streampipe = gst.parse_launch("v4l2src device=" + device + " ! video/x-raw-rgb, width=640, height=480 ! ffmpegcolorspace ! vp8enc speed=2 max-latency=2 quality=10.0 max-keyframe-distance=3 threads=5 ! queue2 ! mux. alsasrc device=plughw:1,0 ! audioconvert ! vorbisenc ! queue2 ! mux. webmmux name=mux streamable=true ! tcpclientsink host=" + self.remoteip + " port=" + self.remoteport)
        self.streampipe.set_state(gst.STATE_PLAYING)
        
        #jpeg encoded pipeline
        #streampipe2 = gst.parse_launch("v4l2src device=" + device + " ! video/x-raw-yuv,width=640,height=480 ! jpegenc ! queue2 ! m. alsasrc device=plughw:1,0 ! audioconvert ! vorbisenc ! queue2 ! m. matroskamux name=m streamable=true ! tcpclientsink host=" + remoteip + " port=" + remoteport)
        #streampipe2.set_state(gst.STATE_PLAYING)
        
#        bus = self.receivepipe.get_bus()
#        bus.add_signal_watch()
#        bus.enable_sync_message_emission()
#        bus.connect("message", self.on_message)
#        bus.connect("sync-message::element", self.on_sync_message)
        
        #print "Streaming Started"
    
    def start_streaming_video(self):
        device = self.get_camera_name()
        self.receivepipe = gst.parse_launch("tcpserversrc host=" + self.localip + " port=" + self.localport + " ! matroskademux name=d d. ! queue2 ! vp8dec ! ffmpegcolorspace ! xvimagesink name=sink d. ! queue2 ! vorbisdec ! audioconvert ! audioresample ! alsasink sync=false") 
        self.receivepipe.set_state(gst.STATE_PLAYING)
        
        self.streampipe = gst.parse_launch("v4l2src device=" + device + " ! video/x-raw-rgb, width=640, height=480 ! ffmpegcolorspace ! vp8enc speed=2 max-latency=2 quality=10.0 max-keyframe-distance=3 threads=5 ! queue2 ! mux. alsasrc device=plughw:1,0 ! audioconvert ! vorbisenc ! queue2 ! mux. webmmux name=mux streamable=true ! tcpclientsink host=" + self.remoteip + " port=" + self.remoteport)
        self.streampipe.set_state(gst.STATE_PLAYING)
    
    def stop_streaming_video(self):
        self.receivepipe.set_state(gst.STATE_NULL)
        self.streampipe.set_state(gst.STATE_NULL)

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.stop_streaming_video()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.stop_streaming_video()
    
    '''def on_sync_message(self, bus, message):
        if message.structure is None:
            return False
        name = message.structure.get_name()
        if name == "prepare-xwindow-id":
            print self.video_container.window
            gtk.gdk.threads_enter()
            gtk.gdk.display_get_default().sync()
            
            videooutput = message.src
            videooutput.set_property("force-aspect-ratio", True)
            videooutput.set_xwindow_id(self.video_container.window.xid)
            gtk.gdk.threads_leave()'''
