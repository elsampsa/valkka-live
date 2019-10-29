import os
import inspect


def getModulePath():
    lis = inspect.getabsfile(inspect.currentframe()).split("/")
    st = "/"
    for l in lis[:-1]:
        st = os.path.join(st, l)
    return st


def getTestDataPath():
    return os.path.join(getModulePath(), "test_data")


def getTestDataFile(fname):
    return os.path.join(getTestDataPath(), fname)


def getDataPath():
    return os.path.join(getModulePath(), "data")


def getDataFile(fname):
    """Return complete path to datafile fname.  Data files are in the directory aux/aux/data
    """
    return os.path.join(getDataPath(), fname)


def genH264(infile, outfile, T):
    """Generate H264 stream
    
    Input image, output video file, time in seconds
    
    Example:
    
    ::
    
        genH264("/home/sampsa/python3/tests/lprtest/RealImages/IMG_20170308_093511.jpg","testi.mkv", 10)
    
    """
    x264opts="-x264opts keyint=10:min-keyint=10:bframes=0"
    h264_dummystream_flavor="-pix_fmt yuv420p -vprofile main" 

    opts="-vcodec h264 "+h264_dummystream_flavor+" "+x264opts+" -fflags +genpts -r 25 -t "+str(T)
    com="ffmpeg -y -loop 1 -fflags +genpts -r 25 -i "+infile+" "+opts+" "+outfile
    print(com)
    os.system(com)
    
    
# genH264("/home/sampsa/python3/tests/lprtest/RealImages/IMG_20170308_093511.jpg","testi.mkv", 10)
