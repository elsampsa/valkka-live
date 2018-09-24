import sys
# pyeval.py -o/f/h filename.py

if (sys.argv[1]=="-h"):
    print("pyeval.py -o/f/h filename.py")
    print()
    print("for creating automatic .rst files from a .py file")
    print()
    print("o: make output, f: fix output, h: this help")
    print()
    print("pyeval.py -o routine.py > tmp.txt")
    print("pyeval.py -f tmp.txt > routine.rst")
    print()
elif (sys.argv[1]=="-o"):
    f=open(sys.argv[2])
    lines=[]
    c=0
    cc=0
    inst=""
    csec=False
    for line in f.readlines():
        if (line.strip()==""):
            print(inst)
        else:
            st=line[:-1]
            if (st[0]=="#"):
                if (csec==False): # entering comment section.. add extra line
                    print
                print(st)
                csec=True
            else:
                #if (csec==True): # just left comments section.. add extra line
                #    print()
                csec=False 
                print
                print(inst+"["+str(cc)+"]: "+st)
                exec(st)
                cc=cc+1
            c=c+1
else:
    rst_mode=False
    f=open(sys.argv[2])
    lines=[]
    c=0
    inst="    "
    #print
    #print(":: ")
    #print
    for line in f.readlines():
        st=line[:-1]
        if (c==0 and st.strip()!='"""<rtf>'):
          print
          print(":: ")
          print("")
          print(inst+st)
        elif (st.strip()=='"""<rtf>'):
          rst_mode=True
          print
        elif (st.strip()=='<rtf>"""'):
          rst_mode=False
          print("")
          print(":: ")
          print("")
        elif (rst_mode==False):
          print(inst+st)
        else:
          print(st)
        c=c+1
    print
    
    
    