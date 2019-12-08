#include <aws/lambda-runtime/runtime.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <unistd.h>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <fstream>

#include <netdb.h>
#include <unistd.h>
#include <string.h>
#include <sys/fcntl.h>
#include <sys/errno.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <stdio.h>
#include <ifaddrs.h>

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

/* Replace a substring in a string with another (in place) */
void replace_substr(std::string* input, std::string old_substr, std::string new_substr)
{
   std::string int_str("###");    // Hoping no string will have this
   int pos;
   while ((pos = input->find(old_substr)) != std::string::npos)
    input->replace(pos, old_substr.length(), int_str);
   while ((pos = input->find(int_str)) != std::string::npos)
    input->replace(pos, int_str.length(), new_substr);
}

/* Get comma-seperated MAC addresses of all interfaces */
void get_mac_addrs(char* mac)
{
   sprintf(mac, "");

   struct ifreq ifr;
   int s;
   if ((s = socket(AF_INET, SOCK_STREAM,0)) < 0) {
      perror("socket");
      return;
   }

   struct ifaddrs *addrs,*tmp;
   getifaddrs(&addrs);
   tmp = addrs;
   while (tmp)
   {
      if (tmp->ifa_addr && tmp->ifa_addr->sa_family == AF_PACKET)
      {
         strcpy(ifr.ifr_name, tmp->ifa_name);
         if (ioctl(s, SIOCGIFHWADDR, &ifr) < 0) {
            perror("ioctl");
            return;
         }
         
         unsigned char *hwaddr = (unsigned char *)ifr.ifr_hwaddr.sa_data;
         sprintf(mac, "%s,%02X:%02X:%02X:%02X:%02X:%02X", mac, hwaddr[0], hwaddr[1], hwaddr[2],
                     hwaddr[3], hwaddr[4], hwaddr[5]);
      }

      tmp = tmp->ifa_next;
   }

   freeifaddrs(addrs);
   close(s);
}

invocation_response my_handler(invocation_request const& request)
{
   char result[500];

   uint64_t start, end, total_cycles, max_cycles, cnt_cycles;
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

      /* Continuously hit the address with atomic operations */
      // while(1)
      // {
      //    /* atomic sum of cacheline boundary */
      //    __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
      //    uint32_t val = *addr;
      // }

      /* Continuously hit the address with atomic operations */
      total_cycles = 0;
      cnt_cycles = 0;
      max_cycles = 0;
      for (i = 1; i < 10; i++)
      {
         /* Measure memory access latency every millisecond
            * Atomic sum of cacheline boundary, this ensures memory is hit */
         usleep(10000);

         rdtsc();
         __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
         rdtsc1();

         start = ( ((uint64_t)cycles_high << 32) | cycles_low );
         end = ( ((uint64_t)cycles_high1 << 32) | cycles_low1 );
         uint64_t cycles_spent = (end - start);
         total_cycles += cycles_spent;
         if (cycles_spent >= max_cycles)  max_cycles = cycles_spent;
         cnt_cycles ++;
      }

      free(arr);
   }

   // clock_t start_time = clock();
   // while(1)
   // {
   //    if ((clock() - start_time) / CLOCKS_PER_SEC >= 2) // time in seconds
   //       break;
   // }

   /* Prepare response as JSON*/
   char response[1000] = "{ \"Role\" : \"SAMPLER\" ";
   
   /* Add sampler results */
   sprintf(response, "%s, \"Avg Cycles\": \"%lu\"", response, total_cycles/cnt_cycles);
   sprintf(response, "%s, \"Max Cycles\": \"%lu\"", response, max_cycles);
   sprintf(response, "%s, \"Trials\": \"%lu\"", response, cnt_cycles);

   /* Get request id */
   sprintf(response, "%s, \"Request ID\": \"%s\"", response, request.request_id.c_str());

   /* Get MAC addresses and add to the response */
   char mac[50] = "";
   get_mac_addrs(mac);
   sprintf(response, "%s, \"MAC Address\": \"%s\"", response, mac);

   /* Get boot id */
   std::ifstream ifs("/proc/sys/kernel/random/boot_id");
   std::string boot_id ( (std::istreambuf_iterator<char>(ifs) ), (std::istreambuf_iterator<char>()) );
   sprintf(response, "%s, \"Boot ID\": \"%s\"", response, boot_id.c_str());

   /* Close json and escape any quotes in response */
   sprintf(response, "%s }", response);
   std::string *quoted = new std::string(response);
   replace_substr(quoted, "\"", "\\\"");

   /* send response */
   //sprintf(response, "{ \"statusCode\": 200, \"body\": \"%s\" }", quoted->c_str());
   return invocation_response::success(response, "application/json");
}

int main()
{
   run_handler(my_handler);
   return 0;
}