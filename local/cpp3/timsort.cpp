/* 
 * C++ program to perform TimSort. 
 * Courtesy of https://www.geeksforgeeks.org/timsort/ 
 */

#include <bits/stdc++.h>
#include <ctime>
#include <cstdlib>

using namespace std;
using Clock = std::chrono::high_resolution_clock;
using microseconds = std::chrono::microseconds;
using nanoseconds = std::chrono::nanoseconds;
using seconds = std::chrono::seconds;
using std::chrono::duration;
using std::chrono::duration_cast;

const int RUN = 32; 
  
// this function sorts array from left index to 
// to right index which is of size atmost RUN 
void insertionSort(int64_t arr[], int left, int right) 
{ 
    for (int i = left + 1; i <= right; i++) 
    { 
        int64_t temp = arr[i]; 
        int j = i - 1; 
        while (j >= left && arr[j] > temp) 
        { 
            arr[j+1] = arr[j]; 
            j--; 
        } 
        arr[j+1] = temp; 
    } 
} 
  
// merge function merges the sorted runs 
void merge(int64_t arr[], int l, int m, int r) 
{ 
    // original array is broken in two parts 
    // left and right array 
    int len1 = m - l + 1, len2 = r - m; 
    int64_t left[len1], right[len2]; 
    for (int i = 0; i < len1; i++) 
        left[i] = arr[l + i]; 
    for (int i = 0; i < len2; i++) 
        right[i] = arr[m + 1 + i]; 
  
    int i = 0; 
    int j = 0; 
    int k = l; 
  
    // after comparing, we merge those two array 
    // in larger sub array 
    while (i < len1 && j < len2) 
    { 
        if (left[i] <= right[j]) 
        { 
            arr[k] = left[i]; 
            i++; 
        } 
        else
        { 
            arr[k] = right[j]; 
            j++; 
        } 
        k++; 
    } 
  
    // copy remaining elements of left, if any 
    while (i < len1) 
    { 
        arr[k] = left[i]; 
        k++; 
        i++; 
    } 
  
    // copy remaining element of right, if any 
    while (j < len2) 
    { 
        arr[k] = right[j]; 
        k++; 
        j++; 
    } 
} 
  
// iterative Timsort function to sort the 
// array[0...n-1] (similar to merge sort) 
void timSort(int64_t arr[], int n) 
{ 
    // Sort individual subarrays of size RUN 
    for (int i = 0; i < n; i += RUN) 
        insertionSort(arr, i, min((i+RUN-1), (n-1))); 
  
    // start merging from size RUN (or 32). It will merge 
    // to form size 64, then 128, 256 and so on .... 
    for (int size = RUN; size < n; size = 2*size) 
    { 
        // pick starting point of left sub array. We 
        // are going to merge arr[left..left+size-1] 
        // and arr[left+size, left+2*size-1] 
        // After every merge, we increase left by 2*size 
        for (int left = 0; left < n; left += 2*size) 
        { 
            // find ending point of left sub array 
            // mid+1 is starting point of right sub array 
            int mid = left + size - 1; 
            int right = min((left + 2*size - 1), (n-1)); 
  
            // merge sub array arr[left.....mid] & 
            // arr[mid+1....right] 
            if (mid < right)
                merge(arr, left, mid, right); 
        }
    } 
}

// utility function to print the Array 
void printArray(int64_t arr[], int n) 
{ 
    for (int i = 0; i < n; i++) 
        printf("%ld  ", arr[i]); 
    printf("\n"); 
} 
  
// Driver program to test above function 
// Takes 1.5ms on my local box for 5000 elements - Reasonable.
int timsort_main() 
// int main() 
{ 
    srand(time(NULL));

    const int LEN = 5000;
    int64_t arr[LEN]; 
    int n = sizeof(arr)/sizeof(arr[0]); 
    for(int i = 0; i < n; i++)
        arr[i] = rand() % 10000;

    // printf("Given Array is\n"); 
    // printArray(arr, n); 
  
    nanoseconds before = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
    timSort(arr, n); 
    nanoseconds after = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
  
    // printf("After Sorting Array is\n"); 
    // printArray(arr, n); 

    int i;
    for (i = 0; i < n; i++)
        if (i > 0 && arr[i-1] > arr[i])
            break;
    if (i != n) {
        printf("ERROR! Array not sorted properly!\n");
        return -1;
    }

    printf("Time taken (ns): %ld\n", (after - before).count());
    return 0; 
} 