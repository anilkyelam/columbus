/* Main handler for the lambda implementing neighbor discovery and 
 * covert channel communication on AWS
 * 
 * Author: Anil Yelam
 */

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
#include <chrono>
#include <vector>

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

char const TAG[] = "MEMBUS";

/****** Assumptions around clocks ********
 * 1. Clocks have a precision of microseconds or lower.
 * 2. Context switching/core switching would not affect the monotonicity or steadiness of the clock on millisecond scales
 */

#define MAX_BITS_IN_ID           10              // Max lambdas = 2^10
#define SAMPLES_PER_SECOND       1000           /* Sampling rate: This is limited by 1) noise under too much sampling            */
                                                /* and 2) post-processing computation (KS test) done for each sample at every bit*/
#define MAX_BIT_DURATION_SECS    5
#define MUS_PER_SEC              1000000
#define MAX_PHASES               15
#define PVALUE_THRESHOLD         0.0
// #define PVALUE_THRESHOLD      0.0005
// #define PVALUE_THRESHOLD      0.0000001
#define DEFAULT_KS_MEAN_CUTOFF   3.0            /* KS Statistic more than this would indicate enough contention to infer 1-bit   */

using Clock = std::chrono::high_resolution_clock;
using microseconds = std::chrono::microseconds;
using seconds = std::chrono::seconds;
using std::chrono::duration;
using std::chrono::duration_cast;

/* Defined in timsort.cpp (Bad practice using extern!) */
extern void timSort(int64_t arr[], int n);
/* Defined in kstest.cpp */
extern double kstest_mean(int64_t* sample1, int size1, bool is_sorted1, int64_t* sample2, int size2, bool is_sorted2);

/* Save all lambdas invoked in this container. */
std::vector<std::string> lambdas;

/* Logging */
bool log_ = false;
std::vector<std::string> logs;
char lbuffer[1000];
#define lprintf(...) {                 \
   if (log_)                           \
      printf(__VA_ARGS__);             \
}


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


/* A fast but good enough pseudo-random number generator. Good enough for what? */
/* Courtesy of https://stackoverflow.com/questions/1640258/need-a-fast-random-generator-for-c */
uint64_t rand_xorshf96(void) {          //period 2^96-1
    static uint64_t x=123456789, y=362436069, z=521288629;
    uint64_t t;
    x ^= x << 16;
    x ^= x >> 5;
    x ^= x << 1;

    t = x;
    x = y;
    y = z;
    z = t ^ x ^ y;
    return z;
}


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
   }
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


/* Buffers to save samples of latencies for post-experiment analysis */
#define MAX_SAMPLES (MAX_BIT_DURATION_SECS*SAMPLES_PER_SECOND)
bool save_samples;
int64_t samples[MAX_SAMPLES];
int64_t base_readings[MAX_SAMPLES];
int base_readings_len = 0;
int64_t bit1_readings[MAX_SAMPLES];
int bit1_readings_len = 0;
double bit1_pvalue;
int64_t bit0_readings[MAX_SAMPLES];
int bit0_readings_len = 0;
double bit0_pvalue;

sample_t base_sample;
sample_t last_sample;

/* Samples membus lock latencies periodically to infer contention. If calibrate is set, uses these readings as baseline. */
int read_bit(uint64_t* addr, microseconds release_time_mus, int bit_duration_secs, 
   bool calibrate, int id, int phase, int round, double* ksvalue)
{
   int i;
   microseconds one_ms = microseconds(1000);
   microseconds ten_ms = microseconds(10000);
   microseconds next = duration_cast<microseconds>(Clock::now().time_since_epoch());
   // int num_samples = calibrate ? BASELINE_SAMPLES : SAMPLES_PER_BIT;
   // int interval_mus = calibrate ? BASELINE_INTERVAL : BIT_INTERVAL_MUS;
   int num_samples = bit_duration_secs * SAMPLES_PER_SECOND;
   int interval_mus = bit_duration_secs * MUS_PER_SEC;
   double sampling_rate_mus = SAMPLES_PER_SECOND * 1.0 / MUS_PER_SEC;

   /* Release a bit early to avoid overruns (and allow for post-processing) */
   release_time_mus -= ten_ms;

   int64_t start, end, mean, count = 0;
   // lprintf("%ld, %ld,\n", next.count(), release_time_mus.count());      /** COMMENT OUT IN REAL RUNS **/
   for (i = 0; i < num_samples && within_time(release_time_mus); i++)
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
      memcpy(base_readings, samples, count * sizeof(samples[0]));
      base_readings_len = count;

      /* Sort the base sample so we don't have to do it every time */
      timSort(base_readings, base_readings_len);
      return 0;   //not used
   }

   *ksvalue = kstest_mean(base_readings, base_readings_len, true, samples, count, false);

   last_sample = prepare_sample(samples, count, false);
   if(*ksvalue >= DEFAULT_KS_MEAN_CUTOFF) {
      if (save_samples && bit1_readings_len == 0){
         memcpy(bit1_readings, samples, count * sizeof(samples[0]));
         bit1_readings_len = count;
         bit1_pvalue = *ksvalue;
      } 
   }
   else {
      if (save_samples && bit0_readings_len == 0){
         memcpy(bit0_readings, samples, count * sizeof(samples[0]));
         bit0_readings_len = count;
         bit0_pvalue = *ksvalue;
      } 
   }

   return *ksvalue >= DEFAULT_KS_MEAN_CUTOFF;        /* Need to figure out the threshold that works for current platform */
}

/* Causes membus locking contention until a certain time */
void write_bit(uint64_t* addr, microseconds release_time_mus)
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


/************************** CHANNEL START ******************************************************/
/* Define everything related to data transmission over the covert channel here */

#define CHANNEL_BIT_INTERVAL_MUS                      500        // 1 ms per bit
#define ATOMIC_OPS_BATCH_SIZE                         10          // do 10 ops before checking timeout
#define MEM_ACCESS_LATENCY_WITH_LOCKING_THRESHOLD     500         // affect on regular memory accesses by membus locking
#define ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD     9000        // affect on locking memory ops by membus locking from another instance



/* Takes a large sized buffer, performs a number of random accesses 
   and reports the time (randomized to increase the possiblity of a cache miss).
   NOTE: It seems like the GCC optimization options are important to properly measure time
 */
#pragma GCC push_options
#pragma GCC optimize ("O0")
uint64_t perform_random_access(void* buffer, size_t buf_size, int num_accesses) {         // TODO: Inline it?
   uint64_t src = 100, rand, start, end;
   rdtsc();
   for(int i = 0; i < num_accesses; i++) {
      rand = rand_xorshf96() % buf_size;
      memcpy(buffer + rand, &src, sizeof(uint64_t));
   }
   rdtsc1();

   start = ( ((int64_t)cycles_high << 32) | cycles_low );
   end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
   return (end - start);
}
#pragma GCC pop_options

/* Takes a large sized buffer, performs a number of random accesses 
   and reports the time (randomized to increase the possiblity of a cache miss).
   NOTE: It seems like the GCC optimization options are important to properly measure time
 */
inline uint64_t perform_exotic_ops(uint64_t* cacheline_addr, int num_accesses) {
   uint64_t start, end;
   rdtsc();
   for (int i = 0; i < ATOMIC_OPS_BATCH_SIZE; i++)
      __atomic_fetch_add(cacheline_addr, 1, __ATOMIC_SEQ_CST);
   rdtsc1();

   start = ( ((int64_t)cycles_high << 32) | cycles_low );
   end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
   return (end - start);
}

/* Send a data segment */
int send_data(std::vector<bool> data, int nbits, microseconds start_time_mus, uint64_t* cacheline_addr, void* big_buffer, size_t big_buf_size) {
   microseconds bit_start_mus, bit_end_mus;
   int num_erasures, erasures[nbits];
   uint64_t start, end, access_cycles, access_count, access_avg, access_thresh, cycles;

   /* Wait till the startpoint */
   microseconds one_ms = microseconds(1000);
   if (poll_wait(start_time_mus - one_ms)){
      printf("ERROR! Already past the start point for covert channel data.\n");
      return 1;
   }

   num_erasures = 0;
   for(int bit_idx = 0; bit_idx < nbits; bit_idx++) { 
      bit_start_mus = start_time_mus + microseconds(bit_idx * CHANNEL_BIT_INTERVAL_MUS);
      bit_end_mus = bit_start_mus + microseconds(CHANNEL_BIT_INTERVAL_MUS);

      /* Checking time takes order of micro-seconds, so do it sparesely to not affect contention-causing.
      * assuming each locking op costs few microseconds, check time every few hundred microseconds
      * Release a bit early to avoid overruns */
      microseconds ten_mus = microseconds(10);
      bit_end_mus -= ten_mus;
      access_cycles = 0;
      access_count = 0;
      bit0_readings_len = 0;
      base_readings_len = 0;
      while (within_time(bit_end_mus))
      {  
         /* if 1 bit, lock the mem bus using atomic ops; else, perform regular memory accesses */
         if (data[bit_idx]){
            cycles = perform_exotic_ops(cacheline_addr, ATOMIC_OPS_BATCH_SIZE);
            access_cycles += cycles;
            if(bit0_readings_len < MAX_SAMPLES)    bit0_readings[bit0_readings_len++] = cycles / ATOMIC_OPS_BATCH_SIZE;
         }
         else{
            cycles = perform_random_access(big_buffer, big_buf_size, ATOMIC_OPS_BATCH_SIZE);
            access_cycles += cycles;
            if(base_readings_len < MAX_SAMPLES)    base_readings[base_readings_len++] = cycles / ATOMIC_OPS_BATCH_SIZE;
         } 
         access_count += ATOMIC_OPS_BATCH_SIZE;
      }

      if (access_count == 0) {
         /* We are past the time for this bit, perhaps the sender was descheduled */
         erasures[num_erasures++] = bit_idx;
         continue;
      }
      access_avg = access_cycles / access_count;
      // printf("Send bit %d, %d - latency: %lu, count: %d\n", bit_idx, data[bit_idx] ? 1 : 0, access_avg, access_count);

      // if access less then threshold, its an erasure
      access_thresh = data[bit_idx] ? ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD : MEM_ACCESS_LATENCY_WITH_LOCKING_THRESHOLD;
      if (access_avg < access_thresh) {
         /* Receiver was not listening during this time */
         erasures[num_erasures++] = bit_idx;
      }
   }

   printf("Sender sent: ");
   for (int i = 0; i < nbits; i++)  printf("%d ", data[i] ? 1 : 0);
   printf("\nSender - erasures:%d\n", num_erasures);
   return 0;
}


/* Receive a data segment */
int receive_data(std::vector<bool> data, int nbits, microseconds start_time_mus, uint64_t* cacheline_addr) {
   microseconds bit_start_mus, bit_end_mus;
   int num_erasures, erasures[nbits];
   uint64_t start, end, access_cycles, access_count, access_avg, cycles;
   std::vector<bool> result;

   /* Wait till the startpoint */
   microseconds one_ms = microseconds(1000);
   if (poll_wait(start_time_mus - one_ms)){
      printf("ERROR! Already past the start point for covert channel data.\n");
      return 1;
   }

   num_erasures = 0;
   for(int bit_idx = 0; bit_idx < nbits; bit_idx++) { 
      bit_start_mus = start_time_mus + microseconds(bit_idx * CHANNEL_BIT_INTERVAL_MUS);
      bit_end_mus = bit_start_mus + microseconds(CHANNEL_BIT_INTERVAL_MUS);

      /* Checking time takes order of micro-seconds, so do it sparesely to not affect contention-causing.
      * assuming each locking op costs few microseconds, check time every few hundred microseconds
      * Release a bit early to avoid overruns */
      microseconds ten_mus = microseconds(10);
      bit_end_mus -= ten_mus;
      access_cycles = 0;
      access_count = 0;
      while (within_time(bit_end_mus))
      {  
         /* receiver just performs exotic ops */
         cycles = perform_exotic_ops(cacheline_addr, ATOMIC_OPS_BATCH_SIZE);
         access_cycles += cycles;
         if(bit0_readings_len < MAX_SAMPLES)    bit0_readings[bit0_readings_len++] = cycles / ATOMIC_OPS_BATCH_SIZE;
         access_count += ATOMIC_OPS_BATCH_SIZE;
      }

      if (access_count == 0) {
         /* We are past the time for this bit, perhaps the receiver was descheduled */
         erasures[num_erasures++] = bit_idx;
         result.push_back(false);
         continue;
      }
      access_avg = access_cycles / access_count;
      // printf("Recv bit %d - latency: %lu, count: %d\n", bit_idx, access_avg, access_count);
      result.push_back(access_avg >= ATOMIC_OPS_LATENCY_WITH_LOCKING_THRESHOLD);
   }

   printf("Recver rcvd: ");
   for (int i = 0; i < nbits; i++)  printf("%d ", result[i] ? 1 : 0);
   printf("\nRecver - erasures:%d\n", num_erasures);
   return 0;
}


/************************** CHANNEL END   ******************************************************/


/* Finds an address on heap that falls on consecutive cache lines */
uint64_t* get_cache_line_straddled_address()
{
   uint64_t *arr;
   int i, size;
   uint64_t *addr;

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
   size = 10 * cacheline_sz / sizeof(uint64_t);
   arr = (uint64_t*) malloc(size * sizeof(uint64_t));
   for (i = 0; i < size; i++ ) arr[i] = 1; 

   /* Find the second cacheline boundary */
   bool first = true;
   for (i = 1; i < size; i++) {
      long address = (long)(arr + i);
      if (address % cacheline_sz == 0) {
         if (!first)
            break;
         first = false;
      }
   }

   if (i == size) {
      lprintf("ERROR! Could not find a cacheline boundary in the array.\n");
      return NULL;
   }
   else {
      addr = (uint64_t*)((uint8_t*)(arr+i-1) + 4);
      lprintf("Found an address that falls on two cache lines: %p\n", (void*) addr);
   }

   // lprintf("Membus latencies with sliding address:\n");
   // for (int j = -8; j < 16; j++) {
   //    uint64_t* cacheline = (uint64_t*)((uint8_t*)(arr+i-1) + j);
   //    rdtsc();
   //    __atomic_fetch_add(cacheline, 1, __ATOMIC_SEQ_CST);
   //    rdtsc1();
   //    uint64_t start = ( ((int64_t)cycles_high << 32) | cycles_low );
   //    uint64_t end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
   //    lprintf("%d,%lu\n", j, (end - start));
   // }

   return (uint64_t*)addr;
}

/* Execute the info exchange protocol where all participating lambdas on a same machine
* learn the id of one (max-id) lambda in each phase. Runs till all lambdas know each 
* other or for a specified number of phases
* If repeat_phases is true, protocol repeats the first phase i.e., in every phase all 
* lambdas try to agree on the same max lambda id  */
result_t* run_membus_protocol(int my_id, microseconds start_time_mus, int max_phases, int max_bits_in_id, int bit_duration_secs, uint64_t* cacheline_addr, bool repeat_phases, double* time_secs)
{
   double pvalue;

   std::clock_t protocol_start, protocol_end;
   microseconds bit_duration = microseconds(bit_duration_secs * MUS_PER_SEC);
   microseconds five_ms = microseconds(5000);
   microseconds ten_ms = microseconds(10000);
   microseconds phase_duration = bit_duration * max_bits_in_id;
   result_t* result = (result_t*) malloc(sizeof(result_t));
   result->num_phases = 0;

   // Sync with other lambdas a few milliseconds early
   if (poll_wait(start_time_mus - ten_ms)){
      lprintf("ERROR! Already past the intitial sync point, bad run for current lambda.\n");
      return result;
   }

   /* Record start timestamp */
   microseconds begin = duration_cast<microseconds>(Clock::now().time_since_epoch());

   /* Calibrate baseline latencies (when no contention) */
   microseconds next_time_mus = start_time_mus + bit_duration;
   read_bit(cacheline_addr, next_time_mus - ten_ms, bit_duration_secs, true, my_id, 0, 0, &pvalue);

   /* Start protocol phases */
   bool advertised = false;
   lprintf("[Lambda-%3d] Phase, Position, Bit, Sent, Read, Lat Size, Lat Mean, Lat Std, Lat Max, Lat Min, Base Size, Base Mean, Base Std, KSValue\n", my_id);

   for (int phase = 0; phase < max_phases; phase++) {
      bool advertising = !advertised;
      int id_read = 0;

      for (int bit_pos = max_bits_in_id - 1; bit_pos >= 0; bit_pos--) {
            bool my_bit = my_id & (1 << bit_pos);
            int bit_read;

            poll_wait(next_time_mus);
            next_time_mus += bit_duration;
            // if (my_id % 2)   next_time_mus += five_ms;

            if (advertising && my_bit) {
               write_bit(cacheline_addr, next_time_mus - ten_ms);      // Write until 10ms before next interval
               bit_read = 1;                                           // When writing a bit, assume that bit read is one.
            }
            else {
               bit_read = read_bit(cacheline_addr, next_time_mus - ten_ms, bit_duration_secs, false, my_id, phase, bit_pos, &pvalue);
            }

            /* Stop advertising if my bit is 0 and bit read is 1 i.e., someone else has higher id than mine */
            if (advertising && !my_bit && bit_read)
               advertising = false;

            id_read = (2 * id_read) + bit_read;     // We get bits in most to least significant order

            /* CAUTION: Below print statement is used in log analysis, changing format may break post-experiment analysis scripts */
            lprintf("[Lambda-%3d] %3d %9d %4d %5d %5d %9d %9lu %8lu %8lu %8lu %10d %10lu %9lu %2.15f\n", 
               my_id, phase, bit_pos, my_bit, advertising && my_bit, bit_read, 
               last_sample.size,
               advertising && my_bit ? 0 : last_sample.mean, 
               advertising && my_bit ? 0 : (long) sqrt(last_sample.variance), 
               advertising && my_bit ? 0 : last_sample.max, 
               advertising && my_bit ? 0 : last_sample.min, 
               base_sample.size, base_sample.mean, (long) sqrt(base_sample.variance), pvalue);              /** COMMENT OUT IN REAL RUNS **/
      }

      lprintf("[Lambda-%d] Phase %d, Id read: %d\n", my_id, phase, id_read);      /** COMMENT OUT IN REAL RUNS **/

      if (id_read == 0)               // End of protocol
            break;

      result->ids[result->num_phases] = id_read;
      result->num_phases++;

      if (!repeat_phases && id_read == my_id)           // My part is done, I will just listen from now on.
            advertised = true;
   }

   /* Record end timestamp */
   microseconds end = duration_cast<microseconds>(Clock::now().time_since_epoch());
   *time_secs = (end - begin).count() * 1.0 / MUS_PER_SEC;
   lprintf("The protocol ran for %.2lf seconds.\n", *time_secs);

   return result;
}

/* Get comma-seperated MAC addresses of all interfaces */
std::string get_mac_addrs()
{
   char mac[50] = "";
   struct ifreq ifr;
   int s;
   if ((s = socket(AF_INET, SOCK_STREAM,0)) < 0) {
      lprintf("ERROR! Could not get socket for MAC address\n");
      return std::string("");
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
            lprintf("ERROR! Could not ioctl for MAC address\n");
            return std::string("");
         }
         
         unsigned char *hwaddr = (unsigned char *)ifr.ifr_hwaddr.sa_data;
         sprintf(mac, "%02X:%02X:%02X:%02X:%02X:%02X", hwaddr[0], hwaddr[1], hwaddr[2],
                     hwaddr[3], hwaddr[4], hwaddr[5]);
      }

      tmp = tmp->ifa_next;
   }

   freeifaddrs(addrs);
   close(s);
   return std::string(mac);
}

/* Get IP address associated with the socket interface 
 * Courtesy of https://stackoverflow.com/questions/49335001/get-local-ip-address-in-c
 */
std::string get_ipaddr(void) {
   int sock = socket(PF_INET, SOCK_DGRAM, 0);
   sockaddr_in loopback;
   if (sock == -1) {
      lprintf("ERROR! Could not get socket for IP address\n");
      return std::string("");
   }

   std::memset(&loopback, 0, sizeof(loopback));
   loopback.sin_family = AF_INET;
   loopback.sin_addr.s_addr = INADDR_LOOPBACK;   // using loopback ip address
   loopback.sin_port = htons(9);                 // using debug port

   if (connect(sock, reinterpret_cast<sockaddr*>(&loopback), sizeof(loopback)) == -1) {
      close(sock);
      lprintf("ERROR! Could not connect to socket for IP addr\n");
      return std::string("");
   }

   socklen_t addrlen = sizeof(loopback);
   if (getsockname(sock, reinterpret_cast<sockaddr*>(&loopback), &addrlen) == -1) {
      close(sock);
      lprintf("ERROR! Could not getsockname for IP addr\n");
      return std::string("");
   }

   close(sock);

   char buf[INET_ADDRSTRLEN];
   if (inet_ntop(AF_INET, &loopback.sin_addr, buf, INET_ADDRSTRLEN) == 0x0) {
      lprintf("ERROR! Could not inet_ntop for IP addr\n");
      std::string("");
   } else {
      return std::string(buf);
   }
}

/* Performs a CPU-bound operation and gets time taken for the operation. (A measure of how much CPU the process is getting...)
 * Turn off GCC optimizations for this piece of code as to avoid any funky changes to the CPU operation.
 */
#pragma GCC push_options
#pragma GCC optimize ("O0")
double get_cpu_cycles_per_operation() {
   int TIMES = 1e8;
   uint64_t x = 0, start, end;
   microseconds begin_time = duration_cast<microseconds>(Clock::now().time_since_epoch());

   rdtsc();
   for(int i = 0; i < TIMES; i++)  x += i;
   rdtsc1();

   start = ( ((int64_t)cycles_high << 32) | cycles_low );
   end = ( ((int64_t)cycles_high1 << 32) | cycles_low1 );
       
   microseconds end_time = duration_cast<microseconds>(Clock::now().time_since_epoch());
   lprintf("Calculating CPU CPI took %.2lf seconds\n", (end_time - begin_time).count() * 1.0 / MUS_PER_SEC);

   return (end - start) * 1.0 / TIMES;
}
#pragma GCC pop_options

/* Get current date/time, format is YYYY-MM-DD.HH:mm:ss */
const std::string current_datetime() {
   time_t     now = time(0);
   struct tm  tstruct;
   char       buf[80];
   tstruct = *localtime(&now);
   strftime(buf, sizeof(buf), "%Y-%m-%d %X", &tstruct);
   return buf;
}

int main(int argc, char** argv)
{
   std::string role;
   int id = 0;
   long start_time_secs;
   bool parsed_id = false, parsed_time = false;
   bool success = true;

   /* Parse Lambda Id */
   if (argc >= 2) {
      std::istringstream iss(argv[1]);
      if (iss >> id && id > 0 && id < (1<<MAX_BITS_IN_ID)) {
         lprintf("Starting lambda: %d\n", id);
         parsed_id = true;
      }
   }
   if (!parsed_id) {
      printf("ERROR! Provide proper id (%d) in [1, %d)\n", id, 1<<MAX_BITS_IN_ID);
      return 1;
   }

   /* Parse protocol start time (Secs since epoch) */
   if (argc >= 3) {       
      std::istringstream iss(argv[2]);
      if (iss >> start_time_secs && start_time_secs >= 1500000000) {
         lprintf("Protocol start time (secs since epoch): %lu\n", start_time_secs);
         parsed_time = true;
      }
   }
   if (!parsed_time) {
      printf("ERROR! Provide proper arg 2: time in seconds since epoch\n");
      return 1;
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
         success = false;
      }
      lprintf("clock precision level: %d\n", prec);

      /* Get cacheline address */
      uint64_t* addr = get_cache_line_straddled_address();
      if (addr == NULL){
         lprintf("Cannot find cacheline straddled address");
         success = false;
      }

      int max_phases = 2;
      int max_bits = 10;
      int bit_duration_secs = 1;
      double protocol_time;
      bool sender = false, receiver = false;

      if (success) {
         result_t* result;

         /* Run id exchange protocol */
         // microseconds start_time_mus = duration_cast<microseconds>(seconds(start_time_secs));
         // result = run_membus_protocol(id, start_time_mus, max_phases, max_bits, bit_duration_secs, addr, false, &protocol_time);
         result_t res;
         res.num_phases = 2;
         res.ids[0] = 101; res.ids[1] = 303;
         result = &res;
         
         // printf("Lambda %d has seen: ", id);
         // for (int i = 0; i < result->num_phases; i++)   printf("%d ", result->ids[i]);
         // printf("\n");

         if (result->ids[0] == id)  sender = true;
         if (!sender && result->ids[1] == id)  receiver = true;
      }

      std::vector<bool> data_to_send;
      int nbits = 500;
      for(int i = 0; i < nbits; i++)   data_to_send.push_back(random() % 2 == 0);
      // for(int i = 0; i < nbits; i++)   data_to_send.push_back(false);
      microseconds start_time_mus = duration_cast<microseconds>(seconds(start_time_secs));

      if (sender){       
         printf("Lambda %d: I'm the sender!\n", id);

         /* Allocate a big buffer for regular memory accesses */
         const size_t DUMMY_BUF_SIZE = pow(2,29);		// 1GB
         void* dummy_buffer = malloc(DUMMY_BUF_SIZE + sizeof(uint64_t));   
         memset(dummy_buffer, 1, DUMMY_BUF_SIZE);     // this is necessary to actually allocate memory

         send_data(data_to_send, nbits, start_time_mus, addr, dummy_buffer, DUMMY_BUF_SIZE);
      }
      if (receiver){     
         printf("Lambda %d: I'm the receiver!\n", id); 
         receive_data(data_to_send, nbits, start_time_mus, addr);
      }
   }

   return 0;
}