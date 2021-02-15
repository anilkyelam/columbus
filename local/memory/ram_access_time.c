// Spawns child processes to get results from multiple trials.
// Best results so far.
// results14.out is good with 2^x datapoints.
// results16.out is better with 1.2^x datapoints 
// Taking median result.

#define _GNU_SOURCE
#define N (1024*4)
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <unistd.h>
#include <sys/resource.h>
#include <sched.h> 
#include <math.h>
#include <string.h>


// Rdtsc blocks
unsigned cycles_low, cycles_high, cycles_low1, cycles_high1;

static __inline__ unsigned long long rdtsc(void)
{
    __asm__ __volatile__ ("RDTSC\n\t"
            "mov %%edx, %0\n\t"
            "mov %%eax, %1\n\t": "=r" (cycles_high), "=r" (cycles_low)::
            "%rax", "rbx", "rcx", "rdx");
}

static __inline__ unsigned long long rdtsc1(void)
{
    __asm__ __volatile__ ("RDTSC\n\t"
            "mov %%edx, %0\n\t"
            "mov %%eax, %1\n\t": "=r" (cycles_high1), "=r" (cycles_low1)::
            "%rax", "rbx", "rcx", "rdx");
}

/* A fast but good enough pseudo-random number generator. Good enough for what? */
/* Courtesy of https://stackoverflow.com/questions/1640258/need-a-fast-random-generator-for-c */
unsigned long rand_xorshf96(void) {          //period 2^96-1
    static unsigned long x=123456789, y=362436069, z=521288629;
    unsigned long t;
    x ^= x << 16;
    x ^= x >> 5;
    x ^= x << 1;

    t = x;
    x = y;
    y = z;
    z = t ^ x ^ y;
    return z;
}


int main()
{
    uint64_t start, end;
    const size_t DUMMY_BUF_SIZE = pow(2,30);		// 1GB
    void* dummy_buffer = malloc(DUMMY_BUF_SIZE + sizeof(uint64_t));   
    memset(dummy_buffer, 1, DUMMY_BUF_SIZE);     // this is necessary to actually allocate memory

    FILE* fptr;
    unsigned long rand;
    uint64_t src = 100;

    fptr = fopen("time_dram", "w");
    fprintf(fptr,"Time\n");
    for(int trials = 0; trials<1000; trials++)
    {
        rdtsc();
        for(int i = 0; i < 10; i++) {
            rand = rand_xorshf96() % DUMMY_BUF_SIZE;
            memcpy(dummy_buffer + rand, &src, sizeof(uint64_t));
        }
        rdtsc1();

        start = ( ((int64_t)cycles_high << 32) | cycles_low );
        end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
        fprintf(fptr, "%lu\n", end-start);
    }
    fclose(fptr);

    fptr = fopen("time_caches", "w");
    fprintf(fptr,"Time\n");
    for(int trials = 0; trials<10000; trials++)
    {
        rdtsc();
        for(int i = 0; i < 10; i++) {
            rand = rand_xorshf96() % 8;
            memcpy(dummy_buffer + rand, &src, sizeof(uint64_t));
        }
        rdtsc1();

        start = ( ((int64_t)cycles_high << 32) | cycles_low );
        end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
        fprintf(fptr, "%lu\n", end-start);
    }
    fclose(fptr);
}
