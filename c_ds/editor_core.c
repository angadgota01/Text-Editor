#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

#define MAX_HISTORY 500
#define MAX_TEXT 5000
#define ALPHABET_SIZE 26
#define MAX_WORD_LEN 64
#define MAX_SUGGESTIONS 5

/* ================= STACK ================= */

typedef struct {
    char data[MAX_HISTORY][MAX_TEXT];
    int top;
} Stack;

static Stack undoStack;
static Stack redoStack;

/* ================= TRIE ================= */

typedef struct TrieNode {
    struct TrieNode* children[ALPHABET_SIZE];
    int is_end;
} TrieNode;

static TrieNode* root = NULL;

/* ================= STACK OPS ================= */

void stack_init(Stack* s) {
    s->top = -1;
}

void stack_clear(Stack* s) {
    s->top = -1;
}

void stack_push(Stack* s, const char* text) {
    if (!text) return;

    if (s->top < MAX_HISTORY - 1) {
        s->top++;
    } else {
        // shift left (discard oldest)
        for (int i = 1; i < MAX_HISTORY; i++)
            strcpy(s->data[i - 1], s->data[i]);
    }
    strncpy(s->data[s->top], text, MAX_TEXT - 1);
    s->data[s->top][MAX_TEXT - 1] = '\0';
}

int stack_pop(Stack* s, char* out) {
    if (s->top < 0) return 0;
    strcpy(out, s->data[s->top--]);
    return 1;
}

int stack_peek(Stack* s, char* out) {
    if (s->top < 0) return 0;
    strcpy(out, s->data[s->top]);
    return 1;
}

/* ================= TRIE OPS ================= */

TrieNode* trie_node() {
    return (TrieNode*)calloc(1, sizeof(TrieNode));
}

void trie_init() {
    root = trie_node();
}

void trie_insert(const char* word) {
    TrieNode* cur = root;
    for (int i = 0; word[i]; i++) {
        char c = tolower(word[i]);
        if (c < 'a' || c > 'z') return;
        int idx = c - 'a';
        if (!cur->children[idx])
            cur->children[idx] = trie_node();
        cur = cur->children[idx];
    }
    cur->is_end = 1;
}

void trie_load_from_file(const char* filename) {
    FILE* f = fopen(filename, "r");
    if (!f) {
        perror("Failed to open dictionary file");
        return;
    }

    char line[MAX_WORD_LEN];
    while (fgets(line, sizeof(line), f)) {
        // Remove newline / carriage return
        line[strcspn(line, "\r\n")] = '\0';
        if (strlen(line) > 0)
            trie_insert(line);
    }

    fclose(f);
}

void dfs_collect(
    TrieNode* node,
    char* buffer,
    int depth,
    char out[MAX_SUGGESTIONS][MAX_WORD_LEN],
    int* count
) {
    if (!node || *count >= MAX_SUGGESTIONS) return;

    if (node->is_end) {
        buffer[depth] = '\0';
        strcpy(out[(*count)++], buffer);
    }

    for (int i = 0; i < ALPHABET_SIZE; i++) {
        if (node->children[i]) {
            buffer[depth] = 'a' + i;
            dfs_collect(node->children[i], buffer, depth + 1, out, count);
        }
    }
}

/* ================= EXPORTS ================= */

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

EXPORT void init() {
    stack_init(&undoStack);
    stack_init(&redoStack);
    trie_init();

    trie_load_from_file("./c_ds/words.txt");
}

EXPORT void free_mem(void* ptr) {
    /* no-op: retained for ABI compatibility */
    (void)ptr;
}

EXPORT void save_file(const char* filename, const char* text) {
    if (!filename || !text) return;

    FILE* f = fopen(filename, "w");
    if (!f) return;

    fputs(text, f);
    fclose(f);
}

EXPORT void push_undo_state(const char* text) {
    stack_push(&undoStack, text);
    stack_clear(&redoStack);
    printf("UNDO TOP: %d\n", undoStack.top);
    printf("undo stack data: %s \n", undoStack.data[undoStack.top]);
}

EXPORT int perform_undo(const char* current, char* out) {
    if (undoStack.top <= 0) return 0;

    stack_push(&redoStack, current);
    undoStack.top--;
    return stack_peek(&undoStack, out);
}

EXPORT int perform_redo(const char* current, char* out) {
    if (redoStack.top < 0) return 0;

    stack_push(&undoStack, current);
    return stack_pop(&redoStack, out);
}

EXPORT int autocomplete(
    const char* prefix,
    char suggestions[MAX_SUGGESTIONS][MAX_WORD_LEN]
) {
    TrieNode* cur = root;
    char buffer[MAX_WORD_LEN];
    int depth = 0;

    for (int i = 0; prefix[i]; i++) {
        char c = tolower(prefix[i]);
        if (c < 'a' || c > 'z') return 0;
        int idx = c - 'a';
        if (!cur->children[idx]) return 0;
        buffer[depth++] = prefix[i];
        cur = cur->children[idx];
    }

    int count = 0;
    dfs_collect(cur, buffer, depth, suggestions, &count);
    return count;
}
