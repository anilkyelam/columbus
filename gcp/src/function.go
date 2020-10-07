// Package p contains an HTTP Cloud Function.
package p

import (
	"fmt"
	"net/http"
    "unsafe"
    "sync/atomic"
    "github.com/dterei/gotsc"
    "time"
)
/*
#include <sys/types.h>
#include <sys/mman.h>
#include <unistd.h>
*/
import "C"

func MembusMetrics(w http.ResponseWriter, r *http.Request) {
	cacheline_sz := uint64(C.sysconf(196))
	fmt.Printf("Cache line size: %d B\n", cacheline_sz)

	int_sz := unsafe.Sizeof(int(0))
	fmt.Printf("Array Integer size: %d B\n", int_sz)
	size := 10 * int(cacheline_sz) / int(int_sz)
	arr := make([]int, size)
	arr_start := unsafe.Pointer(&arr[0])

	// Get the cacheline boundary
	var i int
	for i = 0; i < size; i++ {
		addr := unsafe.Pointer(uintptr(arr_start) + uintptr(i)*unsafe.Sizeof(arr[0]))
		if uintptr(addr) % uintptr(cacheline_sz) == 0 {
			fmt.Println("The address at the beginning boundary of cache line is ", addr)
			break
		}
	}

	if i == size {
		fmt.Println("ERROR! Could not find a cacheline boundary in the array")
	} else {
		var j int
		// Iterate over the memory region
		for j = 0; j < 15; j++ {
			// Address starting from cacheline - 12B
			addr := unsafe.Pointer(uintptr(arr_start) + unsafe.Sizeof(arr[0])*uintptr(i-2) + ((unsafe.Sizeof(arr[0]))/2)*uintptr(1) + uintptr(j))
			fmt.Println("Address: ", addr)
			st_time := time.Now()
			trials := uint64(0)
			total_cycles := uint64(0)

			// Measure CPU cycles for 3 sec
			for {
				tsc := gotsc.TSCOverhead()
				time.Sleep(10 * time.Millisecond)
				var k int
				for k = 1; k < 1000; k++ {
					start := gotsc.BenchStart()
					atomic.AddUintptr((*uintptr)(addr), uintptr(1))
					end := gotsc.BenchEnd()

					cycle_spent := end-start-tsc
					trials++
					total_cycles += cycle_spent
				}

				if time.Since(st_time) >= 3*time.Second {
					break
				}
			}
			fmt.Println("Total average cycles spent: ", total_cycles/trials)
		}
	}
}
