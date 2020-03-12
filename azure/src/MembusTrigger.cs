using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.WebJobs;
using Microsoft.Azure.WebJobs.Extensions.Http;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace Company.Function
{
    public static class MembusTrigger
    {
        [FunctionName("MembusTrigger")]
        public static async Task<IActionResult> Run(
            [HttpTrigger(AuthorizationLevel.Function, "get", "post", Route = null)] HttpRequest req,
            ILogger log)
        {
            log.LogInformation("C# HTTP trigger function processed a request.");

            string name = req.Query["name"];
            string requestBody = await new StreamReader(req.Body).ReadToEndAsync();
            dynamic data = JsonConvert.DeserializeObject(requestBody);
            name = name ?? data?.name;
            string responseMessage = string.Empty;

            unsafe
            {
                // Try finding the cache line address. Use a fixed datastructure for array?
                int i;
                int cacheLineSize = 64;     // Get from system?
                int size = 10 * cacheLineSize;
                byte[] arr = new byte[size];
                long* addr;

                bool first = false;
                for (i = 0; i < size; i++ )
                {
                    fixed(byte* bp = &arr[i])
                    {
                        if ((long)bp % cacheLineSize == 0) {
                            if (!first)  first = true;
                            else break;
                        }
                    }
                }
                
                if (i == size) {
                    return new OkObjectResult("ERROR! Could not find a cacheline boundary in the array.");
                }
                else {
                    fixed(byte* bp = &arr[i])
                    {
                        addr = (long*)((byte*)(bp));
                    }
                    responseMessage += string.Format("Found an address that falls on two cache lines: 0x{0:X}. ", (long) addr);
                    // responseMessage += string.Format("Found an address that starts at cacheline at  i = {0}\n", i);
                }

                fixed(byte* bp = &arr[i])
                {
                    for (int ofst = -16; ofst < 8; ofst++)
                    {
                        addr = (long*)((byte*)(bp + ofst));
                        // Found the cache-line boundary. Hit it with an atomic operation!
                        ulong ts1, ts2, sum = 0;
                        for (i = 0; i < 100; i++)
                        {
                            ts1 = Rdtsc.Timestamp();
                            Interlocked.Increment(ref *addr);
                            ts2 = Rdtsc.Timestamp();        
                            //responseMessage += string.Format("{0},", ts2-ts1);
                            sum += (ts2-ts1);
                        }  
                        responseMessage += string.Format("{0},", sum/100);
                    }
                }
            }

            // string responseMessage = string.IsNullOrEmpty(name)
            //     ? "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response."
            //     : $"Hello, {name}! This HTTP {e} triggered function executed successfully.";

            return new OkObjectResult(responseMessage);
        }
    }
}
