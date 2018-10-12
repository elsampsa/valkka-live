#!/usr/bin/python3

import sys
import time
import numpy

class StdProcess:
    """A class for running machine vision.  
    
    Synchronized reading from the controlling process is achieved by using stdin and stdout.  Individual bitmap frames are read from a temporary file.
    
    Three arguments are needed:

    ::

        image width
        image height
        tmpfilename

    i.e. you can start this file like this:

    ::

        ./example_process1.py 1280 720 /tmp/valkka-tmpfile

    - Once the process has been started, it waits for the STDIN
    - When STDIN receives the string "R\n", the process knows that there is data in the tmpfile
    - Process then reads that tmpfile as a numpy array, does some analysis to that array, and returns the (textual) analysis results by printing them into STDOUT
    - After that, it continues listening STDIN
    - All debugging, etc. information is printed to stderr
    - When STDIN receives the string "X\n" the process exits
    
    Create your own class based on this class (see an example below)
    """
    
    def __init__(self, width, height, filename, verbose = False):
        self.pre = self.__class__.__name__+" : "
        self.width = width
        self.height = height
        self.filename = filename
        self.verbose = verbose
        self.load()
    
    def load(self):
        """At this stage, load your libraries, say, neural network weights etc.
        """
        pass
    
    def report(self,*args):
        if (self.verbose):
            st = self.pre
            for a in args:
                st += str(a)+" "
            st += "\n"
            sys.stderr.write(st)
    
    def run(self, img):
        """This is the place where you want to do your heavy-weight image analysis on the "img" array
        
        Return the (textual) results of the image analysis.  Returning None indicates the image could not be analyzed
        """
        return None
    
    def reset(self):
        """Reset the analyzer state
        """
        pass
    
    def close(self):
        """Close your analyzer (release memory, etc. if necessary)
        """
        pass
    
    def sendReceipt(self):
        """Sends a special string "C\n" to stdout, indicating that we're waiting for the next frame
        """
        sys.stdout.write("C\n"); sys.stdout.flush()
        
    def cycle(self):
        ok = True
        while ok:
            self.report("waiting stdin")
            ch = sys.stdin.read(2)
            self.report("got >%s<\n" % ch[0:-1])
            if (len(ch)<2): # messages should always be 2 characters: the message character + \n
                self.report("fatal error")
                self.close()
                break
            ch=ch[0:-1]
            if (ch=="T"): #     RESET STATE
                self.report("reset state\n")
                self.reset()
                self.sendReceipt()
            elif (ch=="X"): #   EXIT
                self.report("quit\n")
                self.close()
                ok=False
            elif (ch=="R"): #   READ NEW FRAME
                try:
                    img = numpy.load(filename)
                except FileNotFoundError:
                    self.report("could not read tmpfile "+filename)
                    self.sendReceipt()
                else:
                    result = self.run(img)
                    if (result):
                        try:
                            sys.stdout.write(result+"\n") # NOTE: here, give the (textual) results of the image analysis
                            sys.stdout.flush()
                        except IOError:
                            self.report("could not send data")
                    else:
                        self.sendReceipt()
                        
            # ok = False # debugging
        
        

class TestStdProcess(StdProcess):
    """An example subclass
    """
    
    def load(self):
        pass
    
    def run(self, img):
        time.sleep(0.2) # simulate an analysis process that takes some time ..
        st = "Has analyzed "+str(self.cc+1)+" frames.  Current value = "+str(img[1,1,1])
        self.cc += 1
        return st
        
    def reset(self):
        self.cc = 0
    
    def close(self):
        pass



if (__name__ == "__main__"):
    # arguments needed: width, height, tmpfilename
    try:
        width       = int(sys.argv[1])
        height      = int(sys.argv[2])
        filename    = sys.argv[3]
    except Exception as e:
        sys.stderr.write("example_process1.py parameters failed with '"+str(e)+"'\n")
        raise SystemExit()

    p = TestStdProcess(width, height, filename, verbose = False)
    p.cycle()

    print("example_process1.py : bye!")

