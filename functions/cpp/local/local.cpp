#include <cstdio> 
#include <cstdint>
#include <cstring>
#include <cmath>
#include <unistd.h>
#include <ctime>

#include<string>

#define MAX_SAMPLES 1000

/* Rdtsc blocks for time measurements */
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

int main(int argc, char** argv)
{  
    const std::string thrasher = "thrasher";
    const std::string sampler = "sampler";
    const std::string none = "none";
    std::string role;
    std::string role_id("");
    
    uint64_t start, end, total_cycles_spent, *samples;
    int *arr;
    int i, size = 4;   /* 4 * 4B, give it few cache lines */
    uint32_t *addr;    /* Address that falls on two cache lines. */
    std::srand(std::time(nullptr));

    /* Figure out last-level cache line size of this system */
    // long cacheline_sz = sysconf(_SC_LEVEL3_CACHE_LINESIZE);
    long cacheline_sz = sysconf(_SC_LEVEL2_CACHE_LINESIZE);
    printf("Cache line size: %ld B\n", cacheline_sz);
    if (!cacheline_sz) {
        printf("ERROR! Cannot find the cacheline size on this machine\n");
        return 1;
    }

    if (argc >= 2) {
        role_id = std::string(argv[1]);
    }

    /* Allocate an array that spans multiple cache lines */
    size = 10 * cacheline_sz / sizeof(int);
    arr = (int*) malloc(size * sizeof(int));
    samples = (uint64_t*) malloc(MAX_SAMPLES * sizeof(uint64_t));
    for (i = 0; i < size; i++ ) arr[i] = 1;

    /* Find the first cacheline boundary */
    for (i = 1; i < size; i++) {
        long address = (long)(arr + i);
        if (address % cacheline_sz == 0)  break;
    }

    if (i == size) {
        printf("ERROR! Could not find a cacheline boundary in the array.\n");
        exit(-1);
    }
    else {
        addr = (uint32_t*)((uint8_t*)(arr+i-1) + 2);
        printf("Found an address that falls on two cache lines: %p\n", (void*) addr);
    }
    
#ifdef THRASHER
    /* Continuously hit the address with atomic operations */
    role = thrasher + role_id;
    while(1)
    {   
        /* atomic sum of cacheline boundary */
        __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
    }

#elif SAMPLER
    /* Continuously hit the address with atomic operations */
    time_t st_time = time(0);
    int count = 0;
    int rnd;
    uint64_t sum, mean, stdev;
    role = sampler + role_id;
    while(1)
    {
        /* Measure memory access latency every millisecond
         * Atomic sum of cacheline boundary, this ensures memory is hit */
        // usleep(100000);

        // Sleep a random time before measurement
        rnd = 50 + std::rand() % 900;       // Starting measurement somewhere between 50 and 950 micro-seconds
        usleep(rnd);

        rdtsc();
        __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
        rdtsc1();

        // Sleep the remaining time
        usleep(1000-rnd);

        start = ( ((uint64_t)cycles_high << 32) | cycles_low );
        end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
        total_cycles_spent += (end - start);
        samples[count] = (end - start);
        count++;

        if (count >= MAX_SAMPLES)
        {
            sum = 0;
            for (i = 0; i < MAX_SAMPLES; i++)
                sum = sum + samples[i];
            mean = sum / count;

            /*  Compute  variance  and standard deviation  */
            sum = 0;
            for (i = 0; i < MAX_SAMPLES; i++)
                sum = sum + (samples[i] - mean)*(samples[i] - mean);
            stdev = sqrt(sum / count);

            printf("[%s] Latency Mean: %lu, Stdev: %lu, Interval: %ld\n", role.c_str(), mean, stdev, time(0) - st_time);
            total_cycles_spent = 0;
            count = 0;

            //break;
        }
    }

#else
    /* Print cpu clock speed and quit */
    role = none + role_id;
    rdtsc();
    sleep(1);
    rdtsc1();
    start = ( ((uint64_t)cycles_high << 32) | cycles_low );
    end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
    total_cycles_spent = (end - start);
    printf("cycles per second: %lu Mhz\n", total_cycles_spent/1000000);
    printf("Nothing else to do. Pick a role!\n");
#endif

    free(arr);
    return 0;
}