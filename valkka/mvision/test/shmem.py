"""
A stand-alone test for testing QValkkaShmemProcess2

filtergraph:

(LiveThread:livethread) -------------------------------------+  main branch, streaming
                                                             |   
{ForkFrameFilter: fork_filter} <----(AVThread:avthread) << --+  main branch, decoding
               |
      branch 1 +->> (OpenGLThread:glthread)
               |
      branch 2 +--> {IntervalFrameFilter: interval_filter} --> {SwScaleFrameFilter: sws_filter} --> {RGBSharedMemFrameFilter: shmem_filter}
"""
import time
from valkka.core import *
from valkka.mvision.multiprocess import QValkkaShmemProcess2 

image_interval=1000
# define rgb image dimensions
width  =1920//4
height =1080//4

# posix shared memory
shmem_name    ="lesson_4"      # This identifies posix shared memory - must be unique
shmem_buffers =10              # Size of the shmem ringbuffer

# create and fork multiprocesses before any multithreading
p = QValkkaShmemProcess2("test")
p.start()

glthread        =OpenGLThread("glthread")
gl_in_filter    =glthread.getFrameFilter()
                                        
# branch 2
shmem_filter    =RGBShmemFrameFilter(shmem_name, shmem_buffers, width, height)
# shmem_filter    =BriefInfoFrameFilter("shmem") # a nice way for debugging to see of you are actually getting any frames here ..
sws_filter      =SwScaleFrameFilter("sws_filter", width, height, shmem_filter)
interval_filter =TimeIntervalFrameFilter("interval_filter", image_interval, sws_filter)

# fork
fork_filter     =ForkFrameFilter("fork_filter", gl_in_filter, interval_filter)

# main branch
avthread        =AVThread("avthread",fork_filter)
av_in_filter    =avthread.getFrameFilter()

usbthread       =USBDeviceThread("usbthread")
ctx             =USBCameraConnectionContext("/dev/video2", 1, av_in_filter)

glthread.startCall()
avthread.startCall()
usbthread.startCall()

# start decoding
avthread.decodingOnCall()

# start playing usb camera
usbthread.playCameraStreamCall(ctx)

# create an X-window
window_id =glthread.createWindow()
glthread.newRenderGroupCall(window_id)

# maps stream with slot 1 to window "window_id"
context_id=glthread.newRenderContextCall(1,window_id,0)

time.sleep(20) 

print("\nACTIVATE\n")
p.activate(n_buffer=shmem_buffers, image_dimensions=(width, height), shmem_name=shmem_name)
time.sleep(10)

print("\nDEACTIVATE\n")
p.deactivate()
time.sleep(10)

print("\nACTIVATE\n")
p.activate(n_buffer=shmem_buffers, image_dimensions=(width, height), shmem_name=shmem_name)
time.sleep(10)

p.stop()

glthread.delRenderContextCall(context_id)
glthread.delRenderGroupCall(window_id)

# stop decoding
avthread.decodingOffCall()

# stop threads
usbthread.stopCall()
avthread.stopCall()
glthread.stopCall()

print("bye")
