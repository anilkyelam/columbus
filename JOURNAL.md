# 2020

## 09/11
- Seems like it's really easy to figure out if a lambda went through a warm 
  or cold start. Based on this we could even compare colocation clusters across 
  experiments to validate our technique in absence of ground truth.
- Ask Ariana to look into ethical section of the paper (IRB approval?). Can Amazon sue us for affecting performance of others?
- Ariana could also look at literature to figure out some usecases for cooperative lambda colocation
- Check with Shibani for the GCP plot
- For Keerthana, GCP plot and comparing clusters across experiments.


## 09/12
- Looks like there is 100% warm start percentage if we run an exeriment right 
after another one with the same number of lambdas.

## 09/14
- Looked at different variants of Kolmogorov-Smirinov test for separating latency curves.
- Seems like the "Shallow Mean KS Statistic" is the way to go. While all of the KS variants 
  are doing a nice job, shallow mean seems to be at the right spot for accuracy and 
  computational complexity. Look at `plots/*_cdf_09-10.pdf` files to appreciate this.
- To pick thresholds in future, here are the steps we may need to repeat for every region, if not 
  for each lambda size:
  1. Run the experiment with required configuration with -s flag: `python invoke.py -s -p 1`
  2. Look the samples curves: `bash samples.sh [<exp-name>]`
  3. Generate KS statistic CDF curve: `bash ks-values.sh [<exp-name>]`
  4. It should look like a steppy function - pick a threshold based on the step.
  5. Repeat the experiment with this threshold

## 09/15