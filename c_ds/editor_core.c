#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <ctype.h>

#define MAX_HISTORY 200 //this is to perform undo operation just 200 stack 
#define ALPHABET_SIZE 26
#define MAX_WORD_LEN 64
#define MAX_SUGGESTIONS 5

typedef struct TrieNode {
    struct TrieNode* children[ALPHABET_SIZE];
    int is_end;
} TrieNode;

static TrieNode* root = NULL;


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


// Trie Operations
TrieNode* create_node() {
    TrieNode* node = (TrieNode*)calloc(1, sizeof(TrieNode));
    return node;
}

void trie_init() {
    root = create_node();
}

void trie_insert(const char* word) {
    TrieNode* curr = root;
    for (int i = 0; word[i]; i++) {
        char c = tolower(word[i]);
        if (c < 'a' || c > 'z') return;

        int idx = c - 'a';
        if (!curr->children[idx])
            curr->children[idx] = create_node();

        curr = curr->children[idx];
    }
    curr->is_end = 1;
}

void read_and_insert_into_trie(const char *filename) {
    FILE *file = fopen(filename, "r");
    if (file == NULL) {
        perror("Could not open file");
        return;
    }

    char word[MAX_WORD_LEN];
    while (fgets(word, sizeof(word), file)) {
        // Remove the newline character at the end of the word, if any
        word[strcspn(word, "\n")] = '\0';
        trie_insert(word);  
    }

    fclose(file);
}

void dfs_collect(
    TrieNode* node,
    char* buffer,
    int depth,
    char suggestions[MAX_SUGGESTIONS][MAX_WORD_LEN],
    int* count
) {
    if (*count >= MAX_SUGGESTIONS) return;

    if (node->is_end) {
        buffer[depth] = '\0';
        strcpy(suggestions[*count], buffer);
        (*count)++;
    }

    for (int i = 0; i < ALPHABET_SIZE; i++) {
        if (node->children[i]) {
            buffer[depth] = 'a' + i;
            dfs_collect(node->children[i], buffer, depth + 1, suggestions, count);
        }
    }
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
    trie_init();
    read_and_insert_into_trie("./c_ds/words.txt");

}

EXPORT void push_undo_state(const char* text) {
    if (!text) return;
    push(&undoStack, text);
    
    clearStack(&redoStack); 
}

EXPORT char* perform_undo(const char* current_text) {
    if (undoStack.top <= 0) return NULL;

    char* current = pop(&undoStack);
    push(&redoStack, current);
    free(current);

    return strdup(undoStack.data[undoStack.top]);
}


EXPORT char* perform_redo(const char* current_text) {
    if (redoStack.top <= 0) return NULL;

    char* current = pop(&redoStack);
    push(&undoStack, current);
    free(current);

    return strdup(redoStack.data[redoStack.top]);
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

EXPORT int autocomplete(
    const char* prefix,
    char suggestions[MAX_SUGGESTIONS][MAX_WORD_LEN]
) {
    if (!root || !prefix || prefix[0] == '\0') return 0;

    TrieNode* curr = root;
    char buffer[MAX_WORD_LEN];
    int depth = 0;

    // Traverse using lowercase for matching
    for (int i = 0; prefix[i]; i++) {
        if (depth >= MAX_WORD_LEN - 1) return 0;
        char c = tolower(prefix[i]);
        if (c < 'a' || c > 'z') return 0;  // Reject non-alphabetic 

        int idx = c - 'a';
        if (!curr->children[idx]) return 0;

        // Store the ORIGINAL character (with case) in buffer for later reconstruction
        buffer[depth++] = prefix[i];
        curr = curr->children[idx];
    }

    int count = 0;
    dfs_collect(curr, buffer, depth, suggestions, &count);

    return count;
}
