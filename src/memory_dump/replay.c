#define _LARGEFILE64_SOURCE
#define MIN(a,b) (((a) < (b))?(a):(b))
#include <assert.h>
#include <err.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <errno.h>
#include "pages.h"

/**********************************************************************
 * REPLAY MODE                                                        *
 **********************************************************************/

/* load: restores memory before replay
 * loop_name: name of dumped loop
 * invocation: invocation number to load
 * count: number of args
 * addresses: an array of <count> addresses
 */

#define MAX_WARMUP 64
#define MAX_PAGES 1024

extern int warm(char * addr);
extern void antideadcode(void * n);

static bool loaded = false;
//~ static char backup[MAX_PAGES][PAGESIZE];
static char *warmup[MAX_WARMUP];

//~ static int original_data_counter = 0;
static int hotpages_counter = 0;

char cold[PAGESIZE*200];
char cold2[PAGESIZE*200];

char *get_filename_ext(const char *filename) {
    char *dot = strrchr(filename, '.');
    if(!dot || dot == filename) return "";
    return dot + 1;
}

char *get_filename_without_ext(char *filename) {
    char *dot = strrchr(filename, '.');
    if(!dot || dot == filename) return filename;
    int retstrlen = strlen(filename)-strlen(dot);
    char* retstr = malloc(retstrlen+1);
    strncpy(retstr, filename, retstrlen);
    return retstr;
}

void load(char* loop_name, int invocation, int count, void* addresses[count]) {
    char path[BUFSIZ];
    char buf[BUFSIZ + 1];

    /* Load adresses */
    snprintf(path, sizeof(path), "dump/%s/%d/core.map", loop_name, invocation);
    FILE* core_map = fopen(path, "r");
    if (!core_map) 
        errx(EXIT_FAILURE, "Could not open %s", path);

    while(fgets(buf, BUFSIZ, core_map)) {
        int pos;
        off64_t address;
        sscanf(buf, "%d %lx", &pos, &address);
        addresses[pos] = (char*)(address);
    }
    fclose(core_map);

    if (!loaded) {
        /* load hotpages adresses */
        snprintf(path, sizeof(path), "dump/%s/%d/hotpages.map", loop_name, invocation);
        FILE* hot_map = fopen(path, "r");
        if (!hot_map) 
            warn("REPLAY: Could not open %s", path);

        while(fgets(buf, BUFSIZ, core_map)) {
            off64_t address;
            sscanf(buf, "%lx", &address);
            if (address == 0) continue;
            warmup[hotpages_counter++] = (char*) address;
            if (hotpages_counter >= MAX_WARMUP) break; 
        }
        fclose(hot_map);
        
        loaded = true;
    }

    DIR *dir;
    struct dirent *ent;
    struct stat st;
    int fp;
    char line[PAGESIZE];
    int len;
    char filename[1024];
    int total_readed_bytes=0;

    snprintf(path, sizeof(path), "dump/%s/%d/", loop_name, invocation);
    if ((dir = opendir(path)) == NULL) {
        /* could not open directory */
        fprintf(stderr, "REPLAY: Could not open %s", path);
        exit(EXIT_FAILURE);
    }

    while ((ent = readdir (dir)) != NULL) {
        /* Read *.memdump files */
        if(strcmp(get_filename_ext(ent->d_name), "memdump") != 0) 
          continue;

        snprintf(filename, sizeof(filename), "dump/%s/%d/%s", loop_name, invocation, ent->d_name);
        if (stat(filename, &st) != 0) {
            fprintf(stderr, "Could not get size for file %s: %s\n", filename, strerror(errno));
            exit(EXIT_FAILURE);
        }

        fp = open(filename, O_RDONLY);
        if (fp < 0) {
            fprintf(stderr, "Could not open %s\n", filename);
            exit(EXIT_FAILURE);
        }

        off64_t address;
        sscanf(get_filename_without_ext(ent->d_name), "%lx", &address);

        int read_bytes=0;
        while ((len = read(fp, (char*)(address+read_bytes), PAGESIZE)) > 0) {
            read_bytes+=len;
        }
        printf("Wrote %d at %lx-%lx\n", read_bytes, address, address+read_bytes);

        close(fp);
        //fprintf(stderr, "%d Page(s) (%d bytes) Needed for %s (size = %ldK)\n", readed_bytes/PAGESIZE, readed_bytes, ent->d_name, st.st_size/1024);
    }

    closedir(dir);

    /* Randomize initial state */
    for (int i=0; i < PAGESIZE; i++)
        for (int j=0; j < PAGESIZE*100; j++)
            cold[j] = cold[i]*j;

    /* Restore cache state */
    for (int j=0; j < 3; j++)
        for (int i=0; i < hotpages_counter; i++) 
            warm(warmup[i]);
}