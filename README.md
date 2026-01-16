# Text Editor

## How to Run:

Compile the C files:

Linux
gcc -shared -fPIC -o ./c_ds/libds.so ./c_ds/editor_core.c

macOS
clang -shared -fPIC ./c_ds/editor_core.c -o ./c_ds/libds.so

Windows (MinGW)
gcc -shared -o ./c_ds/libds.dll ./c_ds/editor_core.c

Then run Text editor.py, from the root folder

## Functionality:
-Undo
-Redo
-Save File
-Multiple Fonts and Font Sizes
