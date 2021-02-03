#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>
#include <bits/stdc++.h>
#include <dirent.h>
#include <sys/types.h>

#include <iostream>
#include <fstream>
#include <regex>

using namespace std;
using Clock = std::chrono::high_resolution_clock;
using microseconds = std::chrono::microseconds;
using nanoseconds = std::chrono::nanoseconds;
using seconds = std::chrono::seconds;
using std::chrono::duration;
using std::chrono::duration_cast;


/* Defined in timsort.cpp (Bad practice using extern!) */
extern void timSort(int64_t arr[], int n);


/* Return Kolmogorov-Smirinov statistic between two samples.
 * Instead of maximum difference between eCDFs, this variant returns mean of the 
 * difference between eCDFs taken at every element in both samples.
 */
double kstest_mean(int64_t* sample1, int size1, bool is_sorted1, 
    int64_t* sample2, int size2, bool is_sorted2) 
{
    /* Some big number as numerator to keep computations in integer space (limits sample size to ~ O(1000)) */
    const int64_t SOME_BIG_NUMBER = 1e9;
    const int64_t NO_VAL = -1e9;

    /* Sort if not sorted */
    if (!is_sorted1)    timSort(sample1, size1);
    if (!is_sorted2)    timSort(sample2, size2);
        
    
    int m = size1;
    int n = size2;
    int64_t s1_incr = SOME_BIG_NUMBER / m;
    int64_t s2_incr = SOME_BIG_NUMBER / n;

    int i = 0, j = 0; 
    int64_t s1_accum = 0, s2_accum = 0;
    int64_t s1_accum_prev = 0, s2_accum_prev = 0;
    int64_t max_depth = 0, deep_sum = 0, shallow_sum = 0; 
    while (i < m || j < n) {
        /* save previous values */
        s1_accum_prev = s1_accum;
        s2_accum_prev = s2_accum;

        int64_t s1_val = i < m ? sample1[i] : NO_VAL;
        int64_t s2_val = j < n ? sample2[j] : NO_VAL;

        /* Sample1 element is the next least */
        if (i < m && (s2_val == NO_VAL || sample1[i] <= s2_val)) {
            // val_now = sample1[i]
            s1_accum += s1_incr;
            i++;
            /* continue if there are duplicates */
            while (i < m && sample1[i] == sample1[i-1]) {
                s1_accum += s1_incr;
                i++;
            }
        }

        /* Sample2 element is the next least */
        if (j < n && (s1_val == NO_VAL || sample2[j] <= s1_val)) {
            // val_now = sample2[j]
            s2_accum += s2_incr;
            j++;
            /* continue if there are duplicates */
            while (j < n && sample2[j] == sample2[j-1]) {
                s2_accum += s2_incr;
                j++;
           }
        }

        // printf("%ld %ld\n", s1_accum, s2_accum);
        int64_t depth = s1_accum - s2_accum;
        shallow_sum += s1_val != s2_val ? std::abs(depth) : abs(2 * depth);
        if (std::abs(max_depth) < std::abs(depth))   max_depth = depth;                /* Take absolute max, but preserve the sign */
    }

    /* Estimate max and mean KS statistics */
    double ks_max = max_depth * 1.0 / SOME_BIG_NUMBER;
    double ks_shallow_mean = (shallow_sum * sqrt(m*n) * 1.0) / (SOME_BIG_NUMBER * (m+n) * sqrt(m+n));

    /* Using mean statistic for now */
    return ks_shallow_mean;
}

/* Utility function to print an array */
void print_array(int64_t arr[], int n) 
{ 
    for (int i = 0; i < n; i++) 
        printf("%ld  ", arr[i]); 
    printf("\n"); 
} 

// Driver program to test above functions
// Takes 1.5ms on my local box for 5000 elements - Reasonable.
int kstest_main() 
// int main() 
{ 
    srand(time(NULL));

    const int LEN = 5000;
    int64_t sample1[LEN]; 
    int64_t sample2[LEN]; 
    for(int i = 0; i < LEN; i++) {
        sample1[i] = rand() % 10000;
        sample2[i] = rand() % 10000;
    }

    nanoseconds before = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
    printf("KS Statistic: %lf\n", kstest_mean(sample1, LEN, false, sample2, LEN, false));
    nanoseconds after = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
    printf("Time taken (ns): %ld\n", (after - before).count());


    /* Local test with available samples, and cross-checking with python script */
    const char* PATH = "../out/09-10-00-28/";
    const int COUNT = 1000;
    struct dirent *entry;
    vector<string> files;
    DIR *dir = opendir(PATH);
    if (dir == NULL) {
        cout << "ERROR! Cannot find directory." << endl;
        return -1;
    }
    while ((entry = readdir(dir)) != NULL)      files.push_back(entry->d_name);

    // Categorize files by lambdas        
    std::vector<string> basefiles(COUNT+1);
    std::vector<string> bit0files(COUNT+1);
    std::vector<string> bit1files(COUNT+1);
    std::regex base("^base_samples([0-9]+)$");
    std::regex bit0("^bit0_samples([0-9]+)$");
    std::regex bit1("^bit1_samples([0-9]+)$");
    std::smatch m;
    for (auto s = begin (files); s != end (files); ++s) {
        string filename = (*s).substr((*s).find_last_of("/\\") + 1);
        // cout << *s << endl;
        if (regex_match(*s, m, base)) {
            basefiles[stoi(m[1])] = *s;
        }
        else if (regex_match(*s, m, bit0)) {
            bit0files[stoi(m[1])] = *s;
        }
        else if (regex_match(*s, m, bit1)){
            bit1files[stoi(m[1])] = *s;
        }
    }

    // Parse files for each lambda
    int size1 = 0, size2 = 0;
    int64_t number;
    std::string line;
    double ks0, ks1;
    int max_time = 0;
    for (int i = 1; i <= COUNT; i++) {
        // cout << basefiles[i] << ", " << bit0files[i] << ", " << bit1files[i] << endl;

        if (basefiles[i].empty())
            continue;

        // Place base latencies in sample1
        size1 = 0;
        ifstream file(string(PATH) + "/" + basefiles[i]);
        while (std::getline(file, line))
        {
            std::istringstream iss(line);
            if (iss >> number)
                sample1[size1++] = number;
        }
        timSort(sample1, size1);

        size2 = 0;
        ks0 = -1;
        if (size1 > 0 && !bit0files[i].empty()) {
            ifstream file(string(PATH) + "/" + bit0files[i]);
            while (std::getline(file, line))
            {
                std::istringstream iss(line);
                if (iss >> number)
                    sample2[size2++] = number;
            }
            
            if (size1 > 0) {
                // printf("bit 0 size: %d\n", size1);
                before = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
                ks0 = kstest_mean(sample1, size1, true, sample2, size2, false);
                after = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
                if ((after - before).count() > max_time)    max_time = (after - before).count();
                printf("%3.3lf\n", ks0);
            }
        }

        size2 = 0;
        ks1 = -1;
        if (size1 > 0 && !bit1files[i].empty()) {
            ifstream file(string(PATH) + "/" + bit1files[i]);
            while (std::getline(file, line))
            {
                std::istringstream iss(line);
                if (iss >> number)
                    sample2[size2++] = number;
            }

            if (size2 > 0) {
                // printf("bit 1 size: %d\n", size2);
                before = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
                ks1 = kstest_mean(sample1, size1, true, sample2, size2, false);
                after = duration_cast<nanoseconds>(Clock::now().time_since_epoch());
                if ((after - before).count() > max_time)    max_time = (after - before).count();         
                printf("%3.3lf\n", ks1);
            }
        }
        
        // printf("%d, %lf, %lf\n", i, ks0, ks1);
        // break;
    }

    printf("Max time per operation (ns): %d\n", max_time);
    closedir(dir);

    return 0; 
} 