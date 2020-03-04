

# Setup 

Azure function can be developed locally (I used VScode) and deployed to Azure directly. 
[This link](
 https://docs.microsoft.com/en-us/azure/azure-functions/functions-develop-vs-code?tabs=csharp#additional-requirements-for-running-a-project-locally) has relevant instructions to enable this functionality in VSCode.
But the essential thing is to have a C# project that is built locally and uploaded to Azure manually or using VSCode extension, etc.

Use the VSCode Azure extension to create/open the project, and create a HTTP trigger after logging into your Azure account.

This needs to be automated.