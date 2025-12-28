# Text Editor

## How to Run:

Compile the C files:
Run the following from within c_ds folder:

macOS
gcc -dynamiclib -o libds.dylib editor_core.c

Linux
gcc -shared -fPIC -o libds.so editor_core.c

Windows (MinGW)
gcc -shared -o libds.dll editor_core.c

Then run Text editor.py, from the root folder

## Functionality:
-Undo
-Redo
-Save File
-Multiple Fonts and Font Sizes