#include <cstdio>
#include <cstdint>
#include <cstring>
#include <string>
#include <unistd.h>
#include <iostream>
#include <sstream>
#include <iomanip>

/* Get current date/time, format is YYYY-MM-DD.HH:mm:ss */
const std::string current_datetime() {
   time_t     now = time(0);
   struct tm  tstruct;
   char       buf[80];
   tstruct = *localtime(&now);
   strftime(buf, sizeof(buf), "%Y-%m-%d %X", &tstruct);
   return buf;
}

int main()
{

   clock_t start_time = clock();
   while(1)
   {
      if ((clock() - start_time) / CLOCKS_PER_SEC >= 2) // time in seconds
         break;
   }

   std::cout << current_datetime() << std::endl;

   return 0;
}