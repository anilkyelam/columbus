#include <aws/lambda-runtime/runtime.h>
#include <cstdio>
#include <cstdint>
#include <string>
#include <unistd.h>

using namespace aws::lambda_runtime;

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

invocation_response my_handler(invocation_request const& request)
{
   int status = 0;
   char result[200];

   uint64_t start, end,total_cycles_spent;
   int* arr;
   int i, size = 4;   /* 4 * 4B, give it few cache lines */
   uint32_t *addr;    /* Address that falls on two cache lines. */

   /* Figure out last-level cache line size of this system */
   long cacheline_sz = sysconf(_SC_LEVEL3_CACHE_LINESIZE);
   printf("Cache line size: %ld B\n", cacheline_sz);

   /* Allocate an array that spans multiple cache lines */
   size = 10 * cacheline_sz / sizeof(int);
   arr = (int*)malloc(size*sizeof(int));
   for (i = 0; i < size; i++ ) arr[i] = 1;

   /* Find the first cacheline boundary */
   for (i = 1; i < size; i++)
   {
      long address = (long)(arr + i);
      if (address % cacheline_sz == 0)  break;
   }

   if (i == size)
   {
      printf("ERROR! Could not find a cacheline boundary in the array.\n");
      sprintf(result, "ERROR! Could not find a cacheline boundary in the array.\n");
   }
   else
   {
      addr = (uint32_t*)((uint8_t*)(arr+i-1) + 2);
      printf("Found an address that falls on two cache lines: %p\n", (void*) addr);
  
      int trials = 1000;
      double op1_cycles, op2_cycles, op3_cycles;

      /* regular sum, no bus contention or DRAM memory access */
      rdtsc();
      for (i = 0; i < trials; i++ )
      {
         (*addr)++;
      } 
      rdtsc1();
      start = ( ((uint64_t)cycles_high << 32) | cycles_low );
      end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
      op1_cycles = (end - start)*1.0/trials;
      printf("Cycles per operation: %lu\n", op1_cycles);

      /* atomic sum of regular addres */
      rdtsc();
      for (i = 0; i < trials; i++ )
      {
         __atomic_fetch_add(arr, 1, __ATOMIC_SEQ_CST);
      } 
      rdtsc1();
      start = ( ((uint64_t)cycles_high << 32) | cycles_low );
      end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
      op2_cycles = (end - start)/trials;
      printf("Cycles per operation: %lu\n", op2_cycles);
      
      /* atomic sum of cacheline boundary */
      rdtsc();
      for (i = 0; i < trials; i++ )
      {
         __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
      } 
      rdtsc1();
      start = ( ((uint64_t)cycles_high << 32) | cycles_low );
      end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
      op3_cycles = (end - start)/trials;
      printf("Cycles per operation: %lf\n", op3_cycles);

      free(arr);
      
      sprintf(result, "Cache line: %ld, Op1 Cycles: %lf, Op2 Cycles: %lf, Op3 Cycles: %lf\n", 
         cacheline_sz, op1_cycles, op2_cycles, op3_cycles);
   }

   printf("%s\n", result);
   return invocation_response::success(request->payload, "application/json");
}

int main()
{
   run_handler(my_handler);
   return 0;
}