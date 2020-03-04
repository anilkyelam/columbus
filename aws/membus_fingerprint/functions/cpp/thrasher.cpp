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
#include <vector>
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
   char result[500];
   std::string role;
   uint64_t start, end;
   double time_taken=0.0;
   int* arr;
   int i, size = 4;   /* 4 * 4B, give it few cache lines */
   uint32_t *addr;    /* Address that falls on two cache lines. */

   /* Figure out last-level cache line size of this system */
   long cacheline_sz = sysconf(_SC_LEVEL3_CACHE_LINESIZE);
   //long cacheline_sz = sysconf(_SC_LEVEL2_CACHE_LINESIZE);
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

      try {
         // Split the payload
         std::istringstream ss(request.payload); 
         std::vector<std::string> params;
         for(std::string s; ss >> s; ){
            params.push_back(s);
         }
         int no_of_thrashers = stoi(params[0]);
         int thrasher_id = stoi(params[1]);
         int interval_length = stoi(params[2]);

         //Sleep and wake pattern
         std::vector<bool> vb(no_of_thrashers, false);
         //Set the index corresponsing the the thrasher ID to true. This wakes up the thrasher
         vb[thrasher_id] = true;

         for (auto bit: vb){
            if(bit){
               time_t st_time = time(0);
               while(1)
               {
                  for (i = 1; i < 1000; i++){
                     /* atomic sum of cacheline boundary */
                     __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
                  }

                  if (time(0) - st_time >= interval_length)
                     break;
               }
            }else{
               sleep(interval_length);
            }
         }
      }
      catch(std::invalid_argument& e){
         // if no conversion could be performed
         role = none;
      }

   }

   // clock_t start_time = clock();
   // while(1)
   // {
   //    if ((clock() - start_time) / CLOCKS_PER_SEC >= 2) // time in seconds
   //       break;
   // }

   /* Prepare response as JSON*/
   char response[1000];
   sprintf(response, "{ \"Role\" : \"%s\" ", role.c_str());

   /* Add time to response */
   sprintf(response, "%s, \"Start Time\": \"%s\"", response, start_time.c_str());
   sprintf(response, "%s, \"End Time\": \"%s\"", response, current_datetime().c_str());


   sprintf(response, "%s, \"Thread time\": \"%lf\"", response, time_taken);

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
