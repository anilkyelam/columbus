#include <cstdio> 
#include <cstdint>
#include <cstring>
#include <cmath>
#include <unistd.h>
#include <ctime>

#include<string>

#define MAX_SAMPLES         1000
#define BIT_INTERVAL        10000000     // 1ms; 1ns=1cycle
#define SAMPLING_INTERVAL   1000        // 1mu-s; 1ns=1cycle

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

double next_poisson_time(double rate)
{
    return -logf(1.0f - ((double) random()) / (double) (RAND_MAX)) / rate;
}

// Might help not putting the process into wait queue
// Also, sleep is not reliable at these time scales
void poll_wait(uint64_t cycles)
{
    uint64_t start, end;
    rdtsc();
    start = ( ((uint64_t)cycles_high << 32) | cycles_low );
    while(1)
    {
        rdtsc();
        end = ( ((uint64_t)cycles_high << 32) | cycles_low );
        if (end - start >= cycles)  return;
    }
}

int read_bit(uint32_t* addr, uint64_t* samples_buf)
{
    int i = 0;
    uint64_t begin, now, next, sofar;
    uint64_t start, end;
    uint64_t tail = 100 * SAMPLING_INTERVAL;
    double rate = 1.0/100;
    int result = -1;

    rdtsc();
    begin = ( ((uint64_t)cycles_high << 32) | cycles_low );

    while(1)
    {   
        // Get a sample
        rdtsc();
        __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
        rdtsc1();

        start = ( ((uint64_t)cycles_high << 32) | cycles_low );
        end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
        samples_buf[i++] = (end - start);

        // Break off with sometime to spare
        rdtsc();
        now = ( ((uint64_t)cycles_high << 32) | cycles_low );
        sofar = now - begin;
        if (sofar + tail >= BIT_INTERVAL)
            break;

        next = (uint64_t) next_poisson_time(rate);

        // Don't go for next sampling if we will end up overtime
        rdtsc();
        now = ( ((uint64_t)cycles_high << 32) | cycles_low );
        sofar = now - begin;
        if (sofar + next + tail >= BIT_INTERVAL)
            break;

        // Wait until next sample
        poll_wait(next * SAMPLING_INTERVAL);
    }

    // Make something out of collected samples
    int j, locked = 0;
    printf("samples (%d): ", i);
    for (j = 0; j < i; j++)
    {   
        // printf("%lu ", samples_buf[j]);
        // TODO: Replace this by a statistical diff test
        // For now, take latency > 1000 as contention and more than half as one bit
        if (samples_buf[j] > 1000)  locked++; 
    }
    result = 2 * locked >= i;
    printf("%d\n", result);
        
    rdtsc();
    now = ( ((uint64_t)cycles_high << 32) | cycles_low );
    sofar = now - begin;
    if (sofar >= BIT_INTERVAL)
        return result;
    
    // Waitout what's left and return
    poll_wait(now - begin);
    return result;
}

void write_bit(uint32_t* addr, bool bit)
{
    int i;
    uint64_t begin, now, sofar;

    if (bit)
    {
        // Write 1, lock membus
        rdtsc();
        begin = ( ((uint64_t)cycles_high << 32) | cycles_low );

        while(1)
        {   
            /* atomic sum of cacheline boundary */
            for (i = 0; i < 10; i++)
                __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
            rdtsc1();

            now = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
            sofar = now - begin;
            if (sofar >= BIT_INTERVAL)
                break;
        }
    }
    else
    {
        // Write 0, do nothing
        poll_wait(BIT_INTERVAL);
    }
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
        // /* atomic sum of cacheline boundary */
        // __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
        write_bit(addr, true);
        write_bit(addr, false);
        write_bit(addr, true);
        write_bit(addr, true);
        write_bit(addr, false);
        write_bit(addr, true);
        write_bit(addr, true);
        write_bit(addr, true);
        write_bit(addr, false);
    }

#elif SAMPLER
    /* Continuously hit the address with atomic operations */
    time_t st_time = time(0);
    int count = 0;
    int rnd;
    uint64_t sum, mean, stdev, min, max;
    FILE *fp = fopen("results", "w+");

    role = sampler + role_id;
    while(1)
    {
        // /* Measure memory access latency every millisecond
        //  * Atomic sum of cacheline boundary, this ensures memory is hit */
        // // usleep(100000);

        // // Sleep a random time before measurement
        // rnd = 50 + std::rand() % 900;       // Starting measurement somewhere between 50 and 950 micro-seconds
        // usleep(rnd);

        // rdtsc();
        // __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
        // rdtsc1();

        // // Sleep the remaining time
        // usleep(1000-rnd);

        // start = ( ((uint64_t)cycles_high << 32) | cycles_low );
        // end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
        // total_cycles_spent += (end - start);
        // samples[count] = (end - start);
        // count++;

        // if (count >= MAX_SAMPLES)
        // {
        //     sum = 0;
        //     for (i = 0; i < MAX_SAMPLES; i++) {
        //         sum = sum + samples[i];
        //         // if (samples[i] > 5000)  fprintf(fp, "%lu\n", samples[i]);
        //         if (samples[i] > 5000)  printf("%lu\n", samples[i]);
        //     }
        //     mean = sum / count;

        //     /*  Compute  variance  and standard deviation  */
        //     sum = 0;
        //     min = 1 << 31;
        //     max = 0;
        //     for (i = 0; i < MAX_SAMPLES; i++)
        //     {
        //         sum = sum + (samples[i] - mean)*(samples[i] - mean);
        //         if (samples[i] > max)   max = samples[i];
        //         if (samples[i] < min)   min = samples[i];
        //     }
        //     stdev = sqrt(sum / count);

        //     printf("[%s] Latency Mean: %lu, Stdev: %lu, Range: %lu, Interval: %ld\n", role.c_str(), mean, stdev, max - min, time(0) - st_time);
        //     total_cycles_spent = 0;
        //     count = 0;

        //     //break;
        // }
        read_bit(addr, samples);
    }

    fclose(fp);

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