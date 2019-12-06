#include <aws/lambda-runtime/runtime.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <unistd.h>
#include <iostream>
#include <sstream>

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

/* From
https://stackoverflow.com/questions/10291882/how-to-deserialize-json-string-in-c-without-using-any-third-party-library
Works only for one level json string.
 */
static std::string get_json_value(std::string json_str, std::string key)
{
   std::stringstream ss(json_str); //simulating an response stream
    const unsigned int BUFFERSIZE = 256;

    //temporary buffer
    char buffer[BUFFERSIZE];
    memset(buffer, 0, BUFFERSIZE * sizeof(char));

    //returnValue.first holds the variables name
    //returnValue.second holds the variables value
    std::pair<std::string, std::string> returnValue;

    //read until the opening bracket appears
    while(ss.peek() != '{')         
    {
        //ignore the { sign and go to next position
        ss.ignore();
    }

    //get response values until the closing bracket appears
    while(ss.peek() != '}')
    {
        //read until a opening variable quote sign appears
        ss.get(buffer, BUFFERSIZE, '\"'); 
        //and ignore it (go to next position in stream)
        ss.ignore();

        //read variable token excluding the closing variable quote sign
        ss.get(buffer, BUFFERSIZE, '\"');
        //and ignore it (go to next position in stream)
        ss.ignore();
        //store the variable name
        returnValue.first = buffer;

        //read until opening value quote appears(skips the : sign)
        ss.get(buffer, BUFFERSIZE, '\"');
        //and ignore it (go to next position in stream)
        ss.ignore();

        //read value token excluding the closing value quote sign
        ss.get(buffer, BUFFERSIZE, '\"');
        //and ignore it (go to next position in stream)
        ss.ignore();
        //store the variable name
        returnValue.second = buffer;

        //do something with those extracted values
        if (key.compare(returnValue.first) == 0)
            return returnValue.second;
    }

    return NULL;
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
  
      const std::string thrasher = "thrasher";
      const std::string sampler = "sampler";
      // std::string role = get_json_value(request.payload, "role");
      // if (thrasher.compare(role) == 0)
      // {
      //    /* Continuously hit the address with atomic operations */
      //    // while(1)
      //    // {
      //    //    /* atomic sum of cacheline boundary */
      //    //    __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
      //    //    uint32_t val = *addr;
      //    // }

      //    sprintf(result, "THRASHER\n");
      // }
      // else if (sampler.compare(role) == 0)
      // {
      //    /* Continuously hit the address with atomic operations */
      //    // while(1)
      //    // {
      //    //    /* Measure memory access latency every millisecond
      //    //       * Atomic sum of cacheline boundary, this ensures memory is hit */
      //    //    usleep(100000);

      //    //    rdtsc();
      //    //    __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
      //    //    rdtsc1();

      //    //    start = ( ((uint64_t)cycles_high << 32) | cycles_low );
      //    //    end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
      //    //    total_cycles_spent = (end - start);
      //    //    printf("Memory access latency in cycles: %lu\n", total_cycles_spent);
      //    // }

      //    sprintf(result, "SAMPLER\n");
      // }
      // else
      // {
      //    /* Print cpu clock speed and quit */
      //    rdtsc();
      //    sleep(1);
      //    rdtsc1();
      //    start = ( ((uint64_t)cycles_high << 32) | cycles_low );
      //    end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
      //    total_cycles_spent = (end - start);
      //    printf("Nothing else to do. Pick a role!\n");
      
      //    sprintf(result, "Cache line: %ld, CPU Speed: %lu Mhz. Nothing else to do. Pick a role!\n", 
      //       cacheline_sz, total_cycles_spent);
      // }

      free(arr);
   }

   printf("%s\n", result);
   return invocation_response::success("anil kumar", "text/plain");
}

int main()
{
   run_handler(my_handler);
   return 0;
}