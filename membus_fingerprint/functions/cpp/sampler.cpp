#include <aws/lambda-runtime/runtime.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <ctime>
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
         sprintf(mac, "%02X:%02X:%02X:%02X:%02X:%02X", hwaddr[0], hwaddr[1], hwaddr[2],
                     hwaddr[3], hwaddr[4], hwaddr[5]);
      }

      tmp = tmp->ifa_next;
   }

   freeifaddrs(addrs);
   close(s);
}

/* Get current date/time, format is YYYY-MM-DD.HH:mm:ss */
const std::string current_datetime() {
   time_t     now = time(0);
   struct tm  tstruct;
   char       buf[80];
   tstruct = *localtime(&now);
   strftime(buf, sizeof(buf), "%Y-%m-%d %X", &tstruct);
   return buf;
}

invocation_response my_handler(invocation_request const& request)
{
   std::string start_time = current_datetime();

   const std::string none = "none";
   std::string role;
   uint64_t start, end;

   std::istringstream ss(request.payload); 
   std::vector<std::string> result;
   for(std::string s; ss >> s; ){
      result.push_back(s);
   }

   int interval_length = stoi(result[0]);
   int no_of_intervals = stoi(result[1]);
   std::vector<uint64_t> cycles(no_of_intervals, 0);
   std::vector<uint64_t> trial(no_of_intervals, 0);
   std::vector<uint64_t> avg_cycles(no_of_intervals, 0);
   double time_taken=0.0;
   int* arr;
   int i, j, size = 4;   /* 4 * 4B, give it few cache lines */
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
   }
   else
   {
      addr = (uint32_t*)((uint8_t*)(arr+i-1) + 2);
      printf("Found an address that falls on two cache lines: %p\n", (void*) addr);

      /* Sample the latency of atomic operations for every interval_length */
      for(j = 0; j < no_of_intervals; j++){
      /* Sample the latency of atomic operations for 5 seconds  */
         for (i = 1; i < interval_length*100; i++)
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
            cycles[j] += cycles_spent;
            trial[j] ++;
         }
      }

      free(arr);
   }


   /* Prepare response as JSON*/
   char response[1000];
   sprintf(response, "{ \"Role\" : \"%s\" ", "sampler");

   /* Add time to response */
   sprintf(response, "%s, \"Start Time\": \"%s\"", response, start_time.c_str());
   sprintf(response, "%s, \"End Time\": \"%s\"", response, current_datetime().c_str());

   /* Add sampler results */
   for(j = 0; j < no_of_intervals; j++){
      avg_cycles[j] = (trial[j]) != 0 ? cycles[j]/trial[j] : 0;
      sprintf(response, "%s, \"Avg Cycles %d\": \"%lu\"", response, j+1, avg_cycles[j]);
   }
   sprintf(response, "%s, \"Thread time\": \"%lf\"", response, time_taken);

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

   /* Close json */
   sprintf(response, "%s }", response);

   /* send response */
   return invocation_response::success(response, "application/json");
}

int main()
{
   run_handler(my_handler);
   return 0;
}