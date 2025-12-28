Text Editor

How to Run:

Compile the C files:
Run the following from within c_ds folder:

macOS
gcc -dynamiclib -o libds.dylib stack.c document.c save.c ds_api.c

Linux
gcc -shared -fPIC -o libds.so stack.c document.c save.c ds_api.c

Windows (MinGW)
gcc -shared -o libds.dll stack.c document.c save.c ds_api.c

Then run Text editor.py, from the root folder

Functionality:
-Undo
-Redo
-Save File