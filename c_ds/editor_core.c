#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define MAX_HISTORY 200 //this is to perform undo operation just 200 stack 


typedef struct {
    char* data[MAX_HISTORY];
    int top;
} Stack;

static Stack undoStack;
static Stack redoStack;


void initStack(Stack* s) {
    s->top = -1;
    for(int i = 0; i < MAX_HISTORY; i++) s->data[i] = NULL;
}

void clearStack(Stack* s) {
    while(s->top >= 0) {
        if (s->data[s->top]) free(s->data[s->top]);
        s->top--;
    }
}


void push(Stack* s, const char* text) {
    if (!text) return;

    
    if (s->top >= MAX_HISTORY - 1) {
        if (s->data[0]) free(s->data[0]);
        
        for (int i = 0; i < s->top; i++) {
            s->data[i] = s->data[i+1];
        }
        s->top--;
    }

    s->top++;
    
    s->data[s->top] = (char*)malloc(strlen(text) + 1);
    if (s->data[s->top]) {
        strcpy(s->data[s->top], text);
    }
}

char* pop(Stack* s) {
    if (s->top >= 0) {
        char* text = s->data[s->top];
        s->top--;
        return text;
    }
    return NULL;
}



#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#elif __APPLE__
#define EXPORT __attribute__((visibility("default")))
#elif __linux__
#define EXPORT __attribute__((visibility("default")))
#else
#define EXPORT
#endif

EXPORT void init() {
    initStack(&undoStack);
    initStack(&redoStack);
}

EXPORT void push_undo_state(const char* text) {
    if (!text) return;
    push(&undoStack, text);
    
    clearStack(&redoStack); 
}

EXPORT char* perform_undo(const char* current_text) {
    
    if (current_text) push(&redoStack, current_text);
    
    
    return pop(&undoStack);
}

EXPORT char* perform_redo(const char* current_text) {
    
    if (current_text) push(&undoStack, current_text);

    
    return pop(&redoStack);
}

EXPORT void save_file(const char* filename, const char* text) {
    if (!filename || !text) return;
    FILE* f = fopen(filename, "w");
    if (f) {
        fprintf(f, "%s", text);
        fclose(f);
    }
}

EXPORT void free_mem(char* ptr) {
    if (ptr) free(ptr);
}