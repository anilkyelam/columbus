/* This file contains methods to perform covert channel communication 
 * using memory bus hardware. Most of the protocol is inspired by 
 * (Algorithm 4) of -
 * "Yu et al. High-speed Covert Channel Attacks in the Cloud, USENIX Security'12"
 * 
 * Author: Anil Yelam
 */

#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>


using Clock = std::chrono::high_resolution_clock;
using microseconds = std::chrono::microseconds;
using seconds = std::chrono::seconds;
using std::chrono::duration;
using std::chrono::duration_cast;


/* Knobs */
#define BIT_INTERVAL_NS     1000        // 1 micro-sec
#define BITS_PER_SEGMENT    64          // Send in 8B segments


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


int send(unsigned char* data, int nbytes, int start_time_mus, char* err_str) {
    microseconds five_ms = microseconds(5000);
    microseconds ten_ms = microseconds(10000);

    // Sync with other lambdas a few milliseconds early
   if (poll_wait(start_time_mus - ten_ms)){
       str err_str"ERROR! Already past the start point, bad run for current lambda.\n");
      return result;
   }
}


int send_bit(int bit) {
    if (bit) {
        // TODO: Perform atomic op and measure 
    }
}

/* Sends data in segment */
int send_raw(uint64_t* buffer, int buf_len) {
    // TODO: Perform solomon-reed encoding for error correction
    int ret, errors, buf_idx, num_bits, num_segments;
    uint64_t data;
    
    num_bits = buf_len * 64
    int num_segments = ceil(num_bits * 1.0 / BITS_PER_SEGMENT);
    buf_idx = 0;
    data = buffer[buf_idx];
    for (int seg_idx = 0, bit_idx = 0; seg_idx < num_segments; seg_idx++) {
        // TODO: Send segment header

        seg_offset = 0;
        errors = 0;
        while(buf_idx < buf_len && seg_offset < BITS_PER_SEGMENT) {
            data = buffer[buf_idx];
            bit = data & (1 << bit_idx);
            ret = send_bit(bit);
            if (ret)    errors++;

            /* Move on to the next bit */
            bit_idx++;
            if (bit_idx == 64){
                bit_idx = 0;
                buf_idx ++;
            }
            seg_offset++;
        }

        // TODO: Send segment footer
        // TODO: Retry on errors
    }

    return 0;
}

void receive() {

}