 


```
main.py
    gui.py
        openValkka()
            - instantiate LiveThread, USBDeviceThread, OpenGLThread, etc.
            - instantiate LiveFilterChainGroup (from filterchain.py):
                LiveFilterChainGroup.chains{list} has instances of MultiForkFilterchain 
                (from chain/multifork.py)     
```

