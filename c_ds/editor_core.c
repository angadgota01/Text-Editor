#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

#define MAX_HISTORY 100
#define MAX_TEXT 10000
#define ALPHABET_SIZE 26
#define MAX_WORD_LEN 64
#define MAX_SUGGESTIONS 5

/* ================= STACK FOR UNDO/REDO ================= */

typedef struct {
    char data[MAX_HISTORY][MAX_TEXT];
    int top;
} Stack;

static Stack undoStack;
static Stack redoStack;

void stack_init(Stack* s) { s->top = -1; }
void stack_clear(Stack* s) { s->top = -1; }

void stack_push(Stack* s, const char* text) {
    if (!text) return;
    if (s->top < MAX_HISTORY - 1) {
        s->top++;
    } else {
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

/* ================= TRIE FOR AUTOCOMPLETE ================= */

typedef struct TrieNode {
    struct TrieNode* children[ALPHABET_SIZE];
    int is_end;
} TrieNode;

static TrieNode* root = NULL;

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
        printf("Dictionary file not found\n");
        return;
    }

    char line[MAX_WORD_LEN];
    while (fgets(line, sizeof(line), f)) {
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

/* ================= WORD COUNT & STATISTICS ================= */

EXPORT int count_words(const char* text) {
    if (!text) return 0;
    
    int count = 0;
    int in_word = 0;
    
    for (int i = 0; text[i]; i++) {
        if (isalnum(text[i])) {
            if (!in_word) {
                count++;
                in_word = 1;
            }
        } else {
            in_word = 0;
        }
    }
    
    return count;
}

EXPORT int count_lines(const char* text) {
    if (!text) return 0;
    
    int count = 1;
    for (int i = 0; text[i]; i++) {
        if (text[i] == '\n') count++;
    }
    return count;
}

EXPORT int count_characters(const char* text) {
    if (!text) return 0;
    return strlen(text);
}

/* ================= FIND & REPLACE ================= */

typedef struct {
    int line;
    int column;
    char context[100];
} FindResult;

static FindResult find_results[100];
static int find_count = 0;

EXPORT int find_text(const char* text, const char* search) {
    if (!text || !search) return 0;
    
    find_count = 0;
    int line = 1;
    int col = 0;
    int text_pos = 0;
    int search_len = strlen(search);
    
    while (text[text_pos] && find_count < 100) {
        int match = 1;
        for (int i = 0; i < search_len; i++) {
            if (tolower(text[text_pos + i]) != tolower(search[i])) {
                match = 0;
                break;
            }
        }
        
        if (match) {
            find_results[find_count].line = line;
            find_results[find_count].column = col;
            
            int start = (text_pos > 30) ? text_pos - 30 : 0;
            int end = text_pos + search_len + 30;
            int ctx_len = 0;
            
            for (int i = start; text[i] && i < end && ctx_len < 99; i++) {
                if (text[i] == '\n') {
                    find_results[find_count].context[ctx_len++] = ' ';
                } else {
                    find_results[find_count].context[ctx_len++] = text[i];
                }
            }
            find_results[find_count].context[ctx_len] = '\0';
            
            find_count++;
            text_pos += search_len;
        } else {
            if (text[text_pos] == '\n') {
                line++;
                col = 0;
            } else {
                col++;
            }
            text_pos++;
        }
    }
    
    return find_count;
}

EXPORT int get_find_result(int index, int* line, int* col, char* context) {
    if (index < 0 || index >= find_count) return 0;
    
    *line = find_results[index].line;
    *col = find_results[index].column;
    strcpy(context, find_results[index].context);
    
    return 1;
}

/* ================= GO TO LINE ================= */

EXPORT int get_line_position(const char* text, int target_line, int* char_position) {
    if (!text) return 0;
    
    int line = 1;
    int pos = 0;
    
    while (text[pos]) {
        if (line == target_line) {
            *char_position = pos;
            return 1;
        }
        
        if (text[pos] == '\n') {
            line++;
        }
        pos++;
    }
    
    return 0;
}

/* ================= AUTO-INDENT ================= */

EXPORT int calculate_indent(const char* text, int line_num) {
    if (!text) return 0;
    
    int current_line = 1;
    int pos = 0;
    int indent = 0;
    
    while (text[pos] && current_line < line_num) {
        if (text[pos] == '\n') current_line++;
        pos++;
    }
    
    if (pos > 0) {
        pos--;
        while (pos > 0 && text[pos] != '\n') pos--;
        if (text[pos] == '\n') pos++;
    }
    
    while (text[pos] == ' ' || text[pos] == '\t') {
        indent++;
        pos++;
    }
    
    int line_end = pos;
    while (text[line_end] && text[line_end] != '\n') line_end++;
    
    for (int i = line_end - 1; i >= pos; i--) {
        if (text[i] == '{' || text[i] == '(' || text[i] == '[') {
            indent += 4;
            break;
        }
    }
    
    return indent;
}

/* ================= DUPLICATE LINE ================= */

EXPORT void duplicate_line(char* text, int line_num, int max_size) {
    if (!text) return;
    
    char result[MAX_TEXT];
    char line_to_dup[1000] = {0};
    int current_line = 1;
    int pos = 0;
    int result_pos = 0;
    int line_start = 0;
    int line_end = 0;
    
    while (text[pos]) {
        if (current_line == line_num) {
            line_start = pos;
            while (text[pos] && text[pos] != '\n') {
                line_to_dup[pos - line_start] = text[pos];
                pos++;
            }
            line_end = pos;
            line_to_dup[pos - line_start] = '\0';
            break;
        }
        if (text[pos] == '\n') current_line++;
        pos++;
    }
    
    if (line_to_dup[0] == '\0') return;
    
    pos = 0;
    while (pos <= line_end && result_pos < MAX_TEXT - 1) {
        result[result_pos++] = text[pos++];
    }
    
    if (result[result_pos - 1] != '\n') {
        result[result_pos++] = '\n';
    }
    
    for (int i = 0; line_to_dup[i] && result_pos < MAX_TEXT - 1; i++) {
        result[result_pos++] = line_to_dup[i];
    }
    
    while (text[pos] && result_pos < MAX_TEXT - 1) {
        result[result_pos++] = text[pos++];
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
}

/* ================= SORT LINES ================= */

int compare_lines(const void* a, const void* b) {
    return strcmp((const char*)a, (const char*)b);
}

EXPORT void sort_lines(char* text, int max_size) {
    if (!text || !*text) return;
    
    char lines[500][256];
    int line_count = 0;
    int pos = 0;
    int line_pos = 0;
    
    while (text[pos] && line_count < 500) {
        if (text[pos] == '\n') {
            lines[line_count][line_pos] = '\0';
            line_count++;
            line_pos = 0;
        } else {
            lines[line_count][line_pos++] = text[pos];
            if (line_pos >= 255) {
                lines[line_count][255] = '\0';
                line_count++;
                line_pos = 0;
            }
        }
        pos++;
    }
    
    if (line_pos > 0) {
        lines[line_count][line_pos] = '\0';
        line_count++;
    }
    
    qsort(lines, line_count, sizeof(lines[0]), compare_lines);
    
    text[0] = '\0';
    for (int i = 0; i < line_count; i++) {
        strcat(text, lines[i]);
        if (i < line_count - 1) {
            strcat(text, "\n");
        }
    }
}

/* ================= WORD FREQUENCY ================= */

typedef struct {
    char word[64];
    int count;
} WordFreq;

static WordFreq word_freq[100];
static int word_freq_count = 0;

EXPORT int analyze_word_frequency(const char* text) {
    if (!text) return 0;
    
    word_freq_count = 0;
    char current_word[64];
    int word_pos = 0;
    
    for (int i = 0; text[i]; i++) {
        if (isalnum(text[i])) {
            if (word_pos < 63) {
                current_word[word_pos++] = tolower(text[i]);
            }
        } else {
            if (word_pos > 0) {
                current_word[word_pos] = '\0';
                
                int found = 0;
                for (int j = 0; j < word_freq_count; j++) {
                    if (strcmp(word_freq[j].word, current_word) == 0) {
                        word_freq[j].count++;
                        found = 1;
                        break;
                    }
                }
                
                if (!found && word_freq_count < 100) {
                    strcpy(word_freq[word_freq_count].word, current_word);
                    word_freq[word_freq_count].count = 1;
                    word_freq_count++;
                }
                
                word_pos = 0;
            }
        }
    }
    
    for (int i = 0; i < word_freq_count - 1; i++) {
        for (int j = 0; j < word_freq_count - i - 1; j++) {
            if (word_freq[j].count < word_freq[j + 1].count) {
                WordFreq temp = word_freq[j];
                word_freq[j] = word_freq[j + 1];
                word_freq[j + 1] = temp;
            }
        }
    }
    
    return word_freq_count;
}

EXPORT int get_word_frequency(int index, char* word, int* count) {
    if (index < 0 || index >= word_freq_count) return 0;
    
    strcpy(word, word_freq[index].word);
    *count = word_freq[index].count;
    
    return 1;
}

/* ================= TOGGLE COMMENT ================= */

EXPORT void toggle_comment(char* text, int line_num, int max_size) {
    if (!text) return;
    
    char result[MAX_TEXT];
    int current_line = 1;
    int pos = 0;
    int result_pos = 0;
    int line_start = -1;
    int line_end = -1;
    
    while (text[pos]) {
        if (current_line == line_num) {
            line_start = pos;
            while (text[pos] && text[pos] != '\n') pos++;
            line_end = pos;
            break;
        }
        if (text[pos] == '\n') current_line++;
        pos++;
    }
    
    if (line_start == -1) return;
    
    int is_commented = 0;
    int check_pos = line_start;
    while (text[check_pos] == ' ' || text[check_pos] == '\t') check_pos++;
    
    if (text[check_pos] == '/' && text[check_pos + 1] == '/') {
        is_commented = 1;
    }
    
    pos = 0;
    while (pos < line_start) {
        result[result_pos++] = text[pos++];
    }
    
    if (is_commented) {
        while (pos < line_end) {
            if (text[pos] == '/' && text[pos + 1] == '/') {
                pos += 2;
                if (text[pos] == ' ') pos++;
                break;
            }
            result[result_pos++] = text[pos++];
        }
        while (pos < line_end) {
            result[result_pos++] = text[pos++];
        }
    } else {
        result[result_pos++] = '/';
        result[result_pos++] = '/';
        result[result_pos++] = ' ';
        while (pos < line_end) {
            result[result_pos++] = text[pos++];
        }
    }
    
    while (text[pos]) {
        result[result_pos++] = text[pos++];
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
}

/* ================= TRIM WHITESPACE ================= */

EXPORT void trim_trailing_whitespace(char* text, int max_size) {
    if (!text) return;
    
    char result[MAX_TEXT];
    int result_pos = 0;
    int pos = 0;
    
    while (text[pos]) {
        int line_end = pos;
        while (text[line_end] && text[line_end] != '\n') line_end++;
        
        int last_char = line_end - 1;
        while (last_char >= pos && (text[last_char] == ' ' || text[last_char] == '\t')) {
            last_char--;
        }
        
        for (int i = pos; i <= last_char && result_pos < MAX_TEXT - 1; i++) {
            result[result_pos++] = text[i];
        }
        
        if (text[line_end] == '\n' && result_pos < MAX_TEXT - 1) {
            result[result_pos++] = '\n';
            pos = line_end + 1;
        } else {
            break;
        }
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
}

/* ================= CASE CONVERSION ================= */

EXPORT void convert_case(char* text, int start, int end, int to_upper) {
    if (!text || start < 0 || end < start) return;
    
    for (int i = start; i < end && text[i]; i++) {
        if (to_upper) {
            text[i] = toupper(text[i]);
        } else {
            text[i] = tolower(text[i]);
        }
    }
}

/* ================= MOVE LINES ================= */

EXPORT void move_line_up(char* text, int line_num, int max_size) {
    if (!text || line_num <= 1) return;
    
    char result[MAX_TEXT];
    char prev_line[1000] = {0};
    char curr_line[1000] = {0};
    int current_line = 1;
    int pos = 0;
    int result_pos = 0;
    
    int prev_start = 0;
    while (text[pos] && current_line < line_num - 1) {
        if (text[pos] == '\n') current_line++;
        pos++;
    }
    prev_start = pos;
    
    int prev_pos = 0;
    while (text[pos] && text[pos] != '\n') {
        prev_line[prev_pos++] = text[pos++];
    }
    if (text[pos] == '\n') pos++;
    
    int curr_start = pos;
    int curr_pos = 0;
    while (text[pos] && text[pos] != '\n') {
        curr_line[curr_pos++] = text[pos++];
    }
    int curr_end = pos;
    
    for (int i = 0; i < prev_start; i++) {
        result[result_pos++] = text[i];
    }
    
    for (int i = 0; curr_line[i]; i++) {
        result[result_pos++] = curr_line[i];
    }
    result[result_pos++] = '\n';
    
    for (int i = 0; prev_line[i]; i++) {
        result[result_pos++] = prev_line[i];
    }
    
    pos = curr_end;
    while (text[pos]) {
        result[result_pos++] = text[pos++];
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
}

EXPORT void move_line_down(char* text, int line_num, int max_size) {
    if (!text) return;
    
    char result[MAX_TEXT];
    char curr_line[1000] = {0};
    char next_line[1000] = {0};
    int current_line = 1;
    int pos = 0;
    int result_pos = 0;
    
    while (text[pos] && current_line < line_num) {
        if (text[pos] == '\n') current_line++;
        pos++;
    }
    
    int curr_start = pos;
    int curr_pos = 0;
    while (text[pos] && text[pos] != '\n') {
        curr_line[curr_pos++] = text[pos++];
    }
    if (text[pos] == '\n') pos++;
    
    int next_pos = 0;
    while (text[pos] && text[pos] != '\n') {
        next_line[next_pos++] = text[pos++];
    }
    int next_end = pos;
    
    if (next_pos == 0) return;
    
    for (int i = 0; i < curr_start; i++) {
        result[result_pos++] = text[i];
    }
    
    for (int i = 0; next_line[i]; i++) {
        result[result_pos++] = next_line[i];
    }
    result[result_pos++] = '\n';
    
    for (int i = 0; curr_line[i]; i++) {
        result[result_pos++] = curr_line[i];
    }
    
    pos = next_end;
    while (text[pos]) {
        result[result_pos++] = text[pos++];
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
}

/* ================= REMOVE EMPTY LINES ================= */

EXPORT void remove_empty_lines(char* text, int max_size) {
    if (!text) return;
    
    char result[MAX_TEXT];
    int result_pos = 0;
    int pos = 0;
    
    while (text[pos]) {
        int line_start = pos;
        
        int is_empty = 1;
        while (text[pos] && text[pos] != '\n') {
            if (text[pos] != ' ' && text[pos] != '\t') {
                is_empty = 0;
            }
            pos++;
        }
        
        if (!is_empty) {
            for (int i = line_start; i <= pos && result_pos < MAX_TEXT - 1; i++) {
                result[result_pos++] = text[i];
            }
        }
        
        if (text[pos] == '\n') pos++;
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
}

/* ================= AUTO-CORRECT FEATURE ================= */

#define MAX_CORRECTIONS 5
#define MAX_EDIT_DISTANCE 2

static int min3(int a, int b, int c) {
    int min = a;
    if (b < min) min = b;
    if (c < min) min = c;
    return min;
}

int levenshtein_distance(const char* s1, const char* s2) {
    int len1 = strlen(s1);
    int len2 = strlen(s2);
    
    if (len1 == 0) return len2;
    if (len2 == 0) return len1;
    
    static int matrix[MAX_WORD_LEN + 1][MAX_WORD_LEN + 1];
    
    for (int i = 0; i <= len1; i++)
        matrix[i][0] = i;
    for (int j = 0; j <= len2; j++)
        matrix[0][j] = j;
    
    for (int i = 1; i <= len1; i++) {
        for (int j = 1; j <= len2; j++) {
            int cost = (tolower(s1[i-1]) == tolower(s2[j-1])) ? 0 : 1;
            
            matrix[i][j] = min3(
                matrix[i-1][j] + 1,
                matrix[i][j-1] + 1,
                matrix[i-1][j-1] + cost
            );
        }
    }
    
    return matrix[len1][len2];
}

typedef struct {
    char word[MAX_WORD_LEN];
    int distance;
} Correction;

static Correction corrections[MAX_CORRECTIONS];
static int correction_count = 0;

void collect_corrections_dfs(
    TrieNode* node,
    const char* target,
    char* buffer,
    int depth
) {
    if (correction_count >= MAX_CORRECTIONS) return;
    if (!node) return;
    
    if (node->is_end && depth > 0) {
        buffer[depth] = '\0';
        
        int dist = levenshtein_distance(target, buffer);
        
        if (dist > 0 && dist <= MAX_EDIT_DISTANCE) {
            if (correction_count < MAX_CORRECTIONS) {
                strcpy(corrections[correction_count].word, buffer);
                corrections[correction_count].distance = dist;
                correction_count++;
                
                for (int i = 0; i < correction_count - 1; i++) {
                    for (int j = 0; j < correction_count - i - 1; j++) {
                        if (corrections[j].distance > corrections[j + 1].distance) {
                            Correction temp = corrections[j];
                            corrections[j] = corrections[j + 1];
                            corrections[j + 1] = temp;
                        }
                    }
                }
            } else {
                if (dist < corrections[MAX_CORRECTIONS - 1].distance) {
                    strcpy(corrections[MAX_CORRECTIONS - 1].word, buffer);
                    corrections[MAX_CORRECTIONS - 1].distance = dist;
                    
                    for (int i = 0; i < correction_count - 1; i++) {
                        for (int j = 0; j < correction_count - i - 1; j++) {
                            if (corrections[j].distance > corrections[j + 1].distance) {
                                Correction temp = corrections[j];
                                corrections[j] = corrections[j + 1];
                                corrections[j + 1] = temp;
                            }
                        }
                    }
                }
            }
        }
    }
    
    for (int i = 0; i < ALPHABET_SIZE; i++) {
        if (node->children[i]) {
            buffer[depth] = 'a' + i;
            collect_corrections_dfs(node->children[i], target, buffer, depth + 1);
        }
    }
}

int word_exists(const char* word) {
    if (!root || !word) return 0;
    
    TrieNode* cur = root;
    for (int i = 0; word[i]; i++) {
        char c = tolower(word[i]);
        if (c < 'a' || c > 'z') return 0;
        
        int idx = c - 'a';
        if (!cur->children[idx]) return 0;
        cur = cur->children[idx];
    }
    
    return cur->is_end;
}

EXPORT int autocorrect(
    const char* word,
    char suggestions[MAX_CORRECTIONS][MAX_WORD_LEN]
) {
    if (!word || strlen(word) == 0) return 0;
    
    if (word_exists(word)) return 0;
    
    correction_count = 0;
    
    char buffer[MAX_WORD_LEN];
    collect_corrections_dfs(root, word, buffer, 0);
    
    for (int i = 0; i < correction_count; i++) {
        strcpy(suggestions[i], corrections[i].word);
    }
    
    return correction_count;
}

EXPORT int get_best_correction(const char* word, char* correction) {
    if (!word || !correction) return 0;
    
    char suggestions[MAX_CORRECTIONS][MAX_WORD_LEN];
    int count = autocorrect(word, suggestions);
    
    if (count > 0) {
        strcpy(correction, suggestions[0]);
        return 1;
    }
    
    return 0;
}

EXPORT int autocorrect_text(char* text, int max_size) {
    if (!text) return 0;
    
    char result[MAX_TEXT];
    int result_pos = 0;
    int corrections_made = 0;
    
    char current_word[MAX_WORD_LEN];
    int word_pos = 0;
    
    for (int i = 0; text[i] && result_pos < MAX_TEXT - 1; i++) {
        if (isalpha(text[i])) {
            if (word_pos < MAX_WORD_LEN - 1) {
                current_word[word_pos++] = text[i];
            }
        } else {
            if (word_pos > 0) {
                current_word[word_pos] = '\0';
                
                char correction[MAX_WORD_LEN];
                if (get_best_correction(current_word, correction)) {
                    for (int j = 0; correction[j] && result_pos < MAX_TEXT - 1; j++) {
                        if (isupper(current_word[0])) {
                            result[result_pos++] = (j == 0) ? toupper(correction[j]) : correction[j];
                        } else {
                            result[result_pos++] = correction[j];
                        }
                    }
                    corrections_made++;
                } else {
                    for (int j = 0; j < word_pos && result_pos < MAX_TEXT - 1; j++) {
                        result[result_pos++] = current_word[j];
                    }
                }
                
                word_pos = 0;
            }
            
            result[result_pos++] = text[i];
        }
    }
    
    if (word_pos > 0) {
        current_word[word_pos] = '\0';
        
        char correction[MAX_WORD_LEN];
        if (get_best_correction(current_word, correction)) {
            for (int j = 0; correction[j] && result_pos < MAX_TEXT - 1; j++) {
                if (isupper(current_word[0])) {
                    result[result_pos++] = (j == 0) ? toupper(correction[j]) : correction[j];
                } else {
                    result[result_pos++] = correction[j];
                }
            }
            corrections_made++;
        } else {
            for (int j = 0; j < word_pos && result_pos < MAX_TEXT - 1; j++) {
                result[result_pos++] = current_word[j];
            }
        }
    }
    
    result[result_pos] = '\0';
    strcpy(text, result);
    
    return corrections_made;
}

/* ================= EXPORTS ================= */

EXPORT void init() {
    stack_init(&undoStack);
    stack_init(&redoStack);
    trie_init();
    trie_load_from_file("./c_ds/words.txt");
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

EXPORT void free_mem(void* ptr) {
    // Placeholder
}
