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


int main()
{
	uint64_t max_size = pow(2,31) + 1;
	int* arr;	
    uint64_t start, end, cycles_spent, total_cycles_spent;
	double avg_cycles_spent;
    int pipefd[2];

	// Set process priority (nice value) to the highest to avoid context switches.
	if(setpriority(PRIO_PROCESS, getpid(), -20) != 0)
	{
		perror("Setting process priority failed!");
		exit(-1);
	}

	for(int trials = 0; trials<1000; trials++)
	{
		int cpid = fork();
		if(cpid == 0)
		{
			for(uint64_t size=2; size < max_size; size *= (size > 100 ? 1.01 : 2))
			{
				arr = (int*)malloc(size*sizeof(int));

				uint64_t next_access = 0, stride = 1, max = 0;
				int temp = arr[next_access];
				while(next_access < size)
				{
					rdtsc();
					temp = arr[next_access];
					rdtsc1();

					start = ( ((uint64_t)cycles_high << 32) | cycles_low );
					end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
					total_cycles_spent = (end - start);
					if(total_cycles_spent > max)
					{
						max = total_cycles_spent;						
					}

					next_access += stride;
					stride *= 2;
				}

				free(arr);
				printf("%lu %lu\n", size, max);
			}

			exit(0);
		}
		else
		{
			wait(NULL);
		}
	}
}
