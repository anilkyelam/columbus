#include <aws/lambda-runtime/runtime.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <string>
#include <unistd.h>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <iomanip>

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

#include "util.h"
#include "RSJparser.tcc"

using namespace aws::lambda_runtime;

/****** Assumptions around clocks ********
 * 1. clocks have a precision of microseconds or lower.
 * 2. Context switching/core switching would not affect the monotonicity or steadiness of the clock on millisecond scales
 * 3. 
 */

#define MAX_BITS_IN_ID      10              // Max lambdas = 2^10
#define BASELINE_SAMPLES    500
#define BASELINE_INTERVAL   1000000         // 1 second to calibrate
#define SAMPLES_PER_BIT     500
#define BIT_INTERVAL_MUS    1000000         // 1 second for communicating each bit
#define MAX_PHASES          15
#define PVALUE_THRESHOLD    0.0005
// #define PVALUE_THRESHOLD    0.0000001

using Clock = std::chrono::high_resolution_clock;
using microseconds = std::chrono::microseconds;
using seconds = std::chrono::seconds;
using std::chrono::duration;
using std::chrono::duration_cast;

/* Defined in ttest.cpp */
extern double welsch_ttest_pvalue(double fmean1, double variance1, int size1, double fmean2, double variance2, int size2);

/* Logging */
bool log_ = false;
std::vector<std::string> logs;
char lbuffer[1000];
#define lprintf(...) {                 \
   if (log_) {                          \
      sprintf(lbuffer, __VA_ARGS__);   \
      logs.push_back(lbuffer);          \
   }                                   \
}

/* Rdtsc blocks for time measurements */
unsigned cycles_low, cycles_high, cycles_low1, cycles_high1;

typedef struct {
   int size;
   int64_t mean;
   int64_t variance;
   int64_t min;
   int64_t max;
} sample_t;

typedef struct {
   int num_phases;
   int ids[MAX_PHASES];
} result_t;

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

/* Prepare randomized seed. Get if from /dev/urandom if possible
* Repurposed from https://stackoverflow.com/questions/2640717/c-generate-a-good-random-seed-for-psudo-random-number-generators*/
unsigned int good_seed(int id)
{
   unsigned int random_seed, random_seed_a, random_seed_b; 
   std::ifstream file("/dev/urandom", std::ios::in|std::ios::binary);
   if (file.is_open())
   {
      char * memblock;
      int size = sizeof(int);
      memblock = new char [size];
      file.read (memblock, size);
      file.close();
      random_seed_a = *reinterpret_cast<int*>(memblock);
      delete[] memblock;
      lprintf("Found urandom file!\n");
   }// end if
   else
   {
      random_seed_a = 0;
   }
   random_seed_b = std::time(0);
   random_seed = random_seed_a xor random_seed_b;
   random_seed = random_seed xor (getpid() << 16);
   random_seed = random_seed xor (id  << 16);
   return random_seed;
} 


/* Check if program is not past specified time yet */
inline bool within_time(microseconds time_pt) {
   microseconds now = duration_cast<microseconds>(Clock::now().time_since_epoch());
   bool within_limit = now.count() < time_pt.count();
   // if (!within_limit) {
   //     // Prints any bad timeoverruns
   //     int64_t ms = (now.count() - time_pt.count()) / 1000;
   //     if (ms > 10) lprintf("Exceeded time limit by more than 10ms: %lu milliseconds\n", ms);
   // }
   return within_limit;
}

/* Stalls the program until a specified point in time */
inline int poll_wait(microseconds release_time)
{
   // If already past the release time, return but in error
   if (!within_time(release_time))
      return 1;

   while(true) {
      microseconds now = duration_cast<microseconds>(Clock::now().time_since_epoch());
      if (now.count() >= release_time.count())
            return 0;
   }
}

inline int64_t get_mean(int64_t* data, int len) 
{
   // Skipped checks
   int64_t sum = 0;
   return sum / len;   
}

/* Removes outliers beyond 3 standard deviations, returns sample params */
inline sample_t prepare_sample(int64_t* data, int len, bool remove_outliers = true)
{
   if (len <= 0) {
      return {
            .size = 0,
            .mean = 0,
            .variance = 0,
            .min = 0,
            .max = 0
      };
   }

   if (len == 1) {
      return {
            .size = len,
            .mean = data[0],
            .variance = 0,
            .min = data[0],
            .max = data[0]
      };
   }

   /* Not using floating point arithmetic at the expense of precision
   * Should be fine as values are in thousands */
   int64_t sum = 0, varsum = 0, mean, var, max = 0, min = 10000000;
   for (int i = 0; i < len; i++) {
         sum += data[i];
         if (data[i] > max)   max = data[i];
         if (data[i] < min)   min = data[i];
   }
   mean = sum / len;
   for (int i = 0; i < len; i++)   varsum += (data[i] - mean) * (data[i] - mean);
   var = varsum / (len - 1);
   int count = len;

   if (remove_outliers) {
      /* X is an outlier if (X - mean) >= 3 * std, or (X - mean)^2 >= 9 * var - to avoid sqrt */
      int i, j;
      sum = 0;
      varsum = 0;
      for (i = 0, j = len - 1, count = 0; i <= j; count++) {
         int64_t sq_diff = (data[i] - mean) * (data[i] - mean);
         if (sq_diff  <= 9 * var) {
               // Keep it 
               sum += data[i];
               varsum += sq_diff;
               i++;
         }
         else {
               // Replace it with last element and continue
               data[i] = data[j];
               j--;
         }
      }
   }

   return {
      .size = count,
      .mean = sum / count,
      .variance = varsum / (count - 1),
      .min = min,
      .max = max
   };
}

/* Samples membus lock latencies periodically to infer contention. If calibrate is set, uses those readings as baseline. */
bool save_samples;
int64_t samples[SAMPLES_PER_BIT];
int64_t saved_readings1[SAMPLES_PER_BIT];
int saved_readings1_len = 0;
int64_t saved_readings2[SAMPLES_PER_BIT];
int saved_readings2_len = 0;

sample_t base_sample;
sample_t last_sample;
int read_bit(uint32_t* addr, microseconds release_time_mus, bool calibrate, int id, int phase, int round, double* pvalue)
{
   int i;
   microseconds one_ms = microseconds(1000);
   microseconds ten_ms = microseconds(10000);
   microseconds next = duration_cast<microseconds>(Clock::now().time_since_epoch());
   int num_samples = calibrate ? BASELINE_SAMPLES : SAMPLES_PER_BIT;
   int interval_mus = calibrate ? BASELINE_INTERVAL : BIT_INTERVAL_MUS;
   double sampling_rate_mus = num_samples * 1.0 / interval_mus;

   /* Checking time takes order of micro-seconds, so do it sparesely to not affect contention-causing.
   * assuming each locking op costs few microseconds, check time every few hundred microseconds
   * Release a bit early to avoid overruns */
   release_time_mus -= ten_ms;
   int64_t start, end, mean, count = 0;
   // lprintf("%ld, %ld,\n", next.count(), release_time_mus.count());      /** COMMENT OUT IN REAL RUNS **/
   for (i = 0; i < SAMPLES_PER_BIT && within_time(release_time_mus); i++)
   {   
      // Get a sample
      rdtsc();
      __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
      rdtsc1();

      start = ( ((int64_t)cycles_high << 32) | cycles_low );
      end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
      samples[i] = (end - start);
      count++;
         
      next += microseconds((int)next_poisson_time(sampling_rate_mus));
      poll_wait(next);
   }

   if (calibrate) {
      base_sample = prepare_sample(samples, count, false);
      if (save_samples){
         memcpy(saved_readings1, samples, sizeof(samples));
         // saved_readings1_len = count;
         saved_readings1_len = base_sample.size;   // no outliers
      } 

      lprintf("Baseline sample: Size- %d, Mean- %lu\n", base_sample.size, base_sample.mean);
      return 0;   //not used
   }
   else {
      last_sample = prepare_sample(samples, count, false);
   }

   //  bool write_to_file = false;                                   /** COMMENT OUT IN REAL RUNS **/       
   //  if (write_to_file) {
   //      char name[100];
   //      sprintf(name, calibrate ? "data/results_base_%d_%d_%d" : "data/results_%d_%d_%d", id, phase, round);
   //      FILE *fp = fopen(name, "w");
   //          fprintf(fp, "Cycles\n");
   //      for (i = 0; i < count; i++) {
   //          fprintf(fp, "%lu\n", samples[i]);
   //      }
   //      fclose(fp);
   //  }

   *pvalue = welsch_ttest_pvalue(base_sample.mean, base_sample.variance, base_sample.size, 
               last_sample.mean, last_sample.variance, last_sample.size);

   if(*pvalue < PVALUE_THRESHOLD) {
      if (save_samples){
         memcpy(saved_readings2, samples, sizeof(samples));
         // saved_readings2_len = count;
         saved_readings2_len = last_sample.size;
      } 
   }

   return *pvalue < PVALUE_THRESHOLD;        /* Need to figure out the threshold that works for current platform */
}

/* Causes membus locking contention until a certain time */
void write_bit(uint32_t* addr, microseconds release_time_mus)
{
   int i;
   microseconds ten_ms = microseconds(10000);

   /* Checking time takes order of micro-seconds, so do it sparesely to not affect contention-causing.
   * assuming each locking op costs few microseconds, check time every few hundred microseconds
   * Release a bit early to avoid overruns */
   release_time_mus -= ten_ms;
   while (within_time(release_time_mus))
   {   
      /* atomic sum of cacheline boundary */
      for (i = 0; i < 1000; i++)
            __atomic_fetch_add(addr, 1, __ATOMIC_SEQ_CST);
   }
}

/* Finds an address on heap that falls on consecutive cache lines */
uint32_t* get_cache_line_straddled_address()
{
   int *arr;
   int i, size;
   uint32_t *addr;

   /* Figure out last-level cache line size of this system */
   long cacheline_sz = sysconf(_SC_LEVEL3_CACHE_LINESIZE);
   if (!cacheline_sz) {
      // If L3 does not exist, try L2.
      cacheline_sz = sysconf(_SC_LEVEL2_CACHE_LINESIZE);
      if (!cacheline_sz) {
            lprintf("ERROR! Cannot find the cacheline size on this machine\n");
            return NULL;
      }
   }
   lprintf("Cache line size: %ld B\n", cacheline_sz);

   /* Allocate an array that spans multiple cache lines */
   size = 10 * cacheline_sz / sizeof(int);
   arr = (int*) malloc(size * sizeof(int));
   for (i = 0; i < size; i++ ) arr[i] = 1; 

   /* Find the first cacheline boundary */
   for (i = 1; i < size; i++) {
      long address = (long)(arr + i);
      if (address % cacheline_sz == 0)  break;
   }

   if (i == size) {
      lprintf("ERROR! Could not find a cacheline boundary in the array.\n");
      return NULL;
   }
   else {
      addr = (uint32_t*)((uint8_t*)(arr+i-1) + 2);
      lprintf("Found an address that falls on two cache lines: %p\n", (void*) addr);
   }

   return addr;
}

/* Execute the info exchange protocol where all participating lambdas on a same machine
* learn the id of one (max-id) lambda in each phase. Runs till all lambdas know each 
* other or for a specified number of phases
* If repeat_phases is true, protocol repeats the first phase i.e., in every phase all 
* lambdas try to agree on the same max lambda id  */
result_t* run_membus_protocol(int my_id, microseconds start_time_mus, int max_phases, uint32_t* cacheline_addr, bool repeat_phases)
{
   double pvalue;
   microseconds bit_duration = microseconds(BIT_INTERVAL_MUS);
   microseconds five_ms = microseconds(5000);
   microseconds ten_ms = microseconds(10000);
   microseconds phase_duration = bit_duration * MAX_BITS_IN_ID;
   result_t* result = (result_t*) malloc(sizeof(result_t));
   result->num_phases = 0;

   // Sync with other lamdas a few milliseconds early
   if (poll_wait(start_time_mus - ten_ms)){
      lprintf("ERROR! Already past the intitial sync point, bad run for current lambda.\n");
      return result;
   }

   // Calibrate baseline latencies (when no contention)
   microseconds next_time_mus = start_time_mus + microseconds(BASELINE_INTERVAL);
   if (my_id % 2)   next_time_mus += five_ms;
   read_bit(cacheline_addr, next_time_mus - ten_ms, true, my_id, 0, 0, &pvalue);

   // Start protocol phases
   bool advertised = false;
   lprintf("[Lambda-%3d] Phase, Position, Bit, Sent, Read, Lat Size, Lat Mean, Lat Std, Lat Max, Lat Min, Base Mean, Base Lat, PValue\n", my_id);
   for (int phase = 0; phase < max_phases; phase++) {
      bool advertising = !advertised;
      int id_read = 0;

      for (int bit_pos = MAX_BITS_IN_ID - 1; bit_pos >= 0; bit_pos--) {
            bool my_bit = my_id & (1 << bit_pos);
            int bit_read;

            poll_wait(next_time_mus);
            next_time_mus += bit_duration;
            if (my_id % 2)   next_time_mus += five_ms;

            if (advertising && my_bit) {
               write_bit(cacheline_addr, next_time_mus - ten_ms);      // Write until 10ms before next interval
               bit_read = 1;                                           // When writing a bit, assume that bit read is one.
            }
            else {
               bit_read = read_bit(cacheline_addr, next_time_mus - ten_ms, false, my_id, phase, bit_pos, &pvalue);
            }

            /* Stop advertising if my bit is 0 and bit read is 1 i.e., someone else has higher id than mine */
            if (advertising && !my_bit && bit_read)
               advertising = false;

            id_read = (2 * id_read) + bit_read;     // We get bits in most to least significant order

            lprintf("[Lambda-%3d] %3d %9d %4d %5d %5d %9d %9lu %8lu %8lu %8lu %10lu %8lu %2.15f\n", 
               my_id, phase, bit_pos, my_bit, advertising && my_bit, bit_read, 
               last_sample.size,
               advertising && my_bit ? 0 : last_sample.mean, 
               advertising && my_bit ? 0 : (long) sqrt(last_sample.variance), 
               advertising && my_bit ? 0 : last_sample.max, 
               advertising && my_bit ? 0 : last_sample.min, 
               base_sample.mean, (long) sqrt(base_sample.variance), pvalue);                          /** COMMENT OUT IN REAL RUNS **/
      }

      lprintf("[Lambda-%d] Phase %d, Id read: %d\n", my_id, phase, id_read);      /** COMMENT OUT IN REAL RUNS **/

      if (id_read == 0)               // End of protocol
            break;

      result->ids[result->num_phases] = id_read;
      result->num_phases++;

      if (!repeat_phases && id_read == my_id)           // My part is done, I will just listen from now on.
            advertised = true;
   }

   return result;
}

/* Get comma-seperated MAC addresses of all interfaces */
void get_mac_addrs(char* mac)
{
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

/* Main entry point */
invocation_response my_handler(invocation_request const& request)
{
   std::string start_time = current_datetime();
   int id, max_phases;
   long start_time_secs;
   bool success = true, sysinfo;
   std::string error;
   result_t* res = NULL;
   
   /* Parse request body for arguments */
   try {     
      RSJresource json(request.payload);
      std::string escaped_body = json["body"].as<std::string>("");
      RSJresource body = RSJresource(util::unescape_json(escaped_body));
      id = body["id"].as<int>(0);
      start_time_secs = body["stime"].as<int>(0);
      log_ = body["log"].as<bool>(false);                   // include logs in response  
      save_samples = body["samples"].as<bool>(false);       // include a sample of latencies in response
      max_phases = body["phases"].as<int>(1);               // run 1 phase by default
   }
   catch(std::exception& e){
      success = false;
      error = "INVALID_BODY";
      lprintf("Could not parse request body\n");
   }

   if (success && id <= 0 || id >= (1<<MAX_BITS_IN_ID)) {
      success = false;
      error = "INVALID_ID";
      lprintf("Id is not provided or invalid (should be in [1, %d)\n", 1<<MAX_BITS_IN_ID);
   }
   
   seconds now = duration_cast<seconds>(Clock::now().time_since_epoch());
   if (success && start_time_secs <= now.count()) {    // Unix time in secs
      success = false;
      error = "INVALID_STIME";
      lprintf("Start time is not provided or is in the past");
   }

   /* Run membus protcol */
   if (success) {
      /* Using a good seed that is different enough for each lambda is critical as 
      * randomness is used in sampling intervals. If these intervals are not random, 
      * lambdas sample the membus at the same time resulting in membus contention 
      * even if none of the lambdas are actually thrashing 
      * NOTE: Purely time-based seed will backfire for applications that start together */
      unsigned int seed = std::time(nullptr) ^ (getpid()<<16 ^ (id << 16));
      // unsigned int seed = good_seed(id);
      std::srand(seed);

      /* Check clock precision on the system is at least micro-seconds (TODO: Does this give real precision?) */
      int prec;
      constexpr auto num = Clock::period::num;
      constexpr auto den = Clock::period::den;
      if (den <= num)                 prec = 0;   // seconds or more
      if (den/num >= 1000)            prec = 1;   // milliseconds or less
      if (den/num >= 1000000)         prec = 2;   // microseconds or less
      if (den/num >= 1000000000)      prec = 3;   // nanoseconds (or less?)
      if (prec < 2) {
         lprintf("Need atleast microsecond precision on wallclock time");
         error = "CLOCK_PRECISION_LOW";
         success = false;
      }
      lprintf("clock precision level: %d\n", prec);

      /* Get cacheline address */
      uint32_t* addr = get_cache_line_straddled_address();
      if (addr == NULL){
         lprintf("Cannot find cacheline straddled address");
         error = "NO_CACHELINE_ADDR";
         success = false;
      }

      if (success) {
         /* Run id exchange protocol */
         microseconds start_time_mus = duration_cast<microseconds>(std::chrono::seconds(start_time_secs));
         res = run_membus_protocol(id, start_time_mus, max_phases, addr, true);
      }
   }

   /* Prepare response body as JSON*/
   RSJresource body("{}");
   // body["request"] = util::escape_json(request.payload);     // Enable this for request payload debugging
   body["Id"] = id;
   body["Start Time"] =  start_time;
   body["End Time"] =   current_datetime();
   body["Request ID"] = request.request_id;

   /* Save results (return all fields whether applicable or not) */
   body["Success"] = success;
   body["Error"] = error;
   body["Phases"] =  res != NULL ? res->num_phases : 0;
   for (int i = 0; i < max_phases; i++) {
      body["Phase " + std::to_string(i+1)] = (res != NULL && i < res->num_phases) ? res->ids[i] : -1;
   }

   /* Save samples if specified */
   if (success && save_samples) {
      std::string arr;
      for (int i = 0; i < saved_readings1_len; i++) {
         arr += std::to_string(saved_readings1[i]) + ',';
      }
      body["Base Sample"] = RSJresource(arr, true);
      
      arr = "";
      for (int i = 0; i < saved_readings2_len; i++) {
         arr += std::to_string(saved_readings2[i]) + ',';
      }
      body["Bit Sample"] = RSJresource(arr, true);
   }

   /* Save some system info */
   /* Get MAC addresses and add to the buffer */ 
   char mac[50] = "";
   get_mac_addrs(mac);
   body["MAC Address"] = std::string(mac);
   /* Get boot id */
   std::ifstream ifs("/proc/sys/kernel/random/boot_id");
   std::string boot_id ( (std::istreambuf_iterator<char>(ifs) ), (std::istreambuf_iterator<char>()) );
   body["Boot ID"] = boot_id;

   /* Save logs to response */
   if (log_) {
      std::string logarr;
      for (std::vector<std::string>::const_iterator it = begin (logs); it != end (logs); ++it) {
         logarr += (*it) + '\t';
      }
      body["Logs"] = RSJresource(logarr, true);
   }

   /* Prepare response with statuscode, headers and body
   * In the format required by Lambda Proxy Integration: 
   * https://aws.amazon.com/premiumsupport/knowledge-center/malformed-502-api-gateway/ */  
   RSJresource response("{}");
   response["statusCode"] = 200;
   response["headers"] = RSJresource("{}");
   std::string escaped_body = util::escape_json(body.as_str());
   response["body"] = RSJresource(escaped_body, true);  // don't parse escaped body as json object

   /* send response */
   return invocation_response::success(response.as_str(), "application/json");
}

int main()
{
   run_handler(my_handler);
   return 0;
}
