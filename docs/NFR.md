This table outlines the Non-Functional Requirements (NFRs) for a GUID (Globally Unique Identifier) service, balancing technical performance with user demand
## Core NFR Comparison

| ID | Category | Requirement Summary | Target Metric |
|---|---|---|---|
| NFR-01 | Throughput | Support peak bursts of activity. | 10 TPS |
| NFR-02 | Availability | Uptime during core business hours (08:00–18:00). | 99.9% |
| NFR-03 | Latency | Fast response times for identifier generation. | < 200ms (p95) |
| NFR-04 | Accuracy | Guarantee no duplicate IDs are generated. | 100% Uniqueness |
| NFR-05 | Reliability | Minimal system errors or timeouts. | 99.99% Success |
| NFR-06 | Recoverability | Maximum time to failover or auto-recover. | < 30s (RTO) |

## Key Insights

* The "Safety Floor": While the average load is very low (~0.09 TPS), the 10 TPS target is a "safety floor." This ensures that if 10% of your users (50 people) hit "Submit" at the exact same moment, the system won't lag or crash.

* Precision vs. Speed: NFR-04 (Accuracy) is the most critical constraint. In a GUID service, latency and throughput matter, but a single "collision" (duplicate ID) could corrupt the integrity of the entire benefit claims database.


While your NFRs are technically sound for a standard service, your multi-cloud architecture (Power Platform → Azure → AWS) introduces several performance bottlenecks that make NFR-03 (Latency) particularly difficult to meet.
The 200ms Latency Challenge (NFR-03)
Achieving a 95th percentile response time of < 200ms is highly ambitious for this specific chain. Each "hop" adds additive latency:
The Multi-Cloud Hop: Traffic moving from the Power Platform (Microsoft) to Azure and then across to AWS API Gateway can easily consume 100–150ms just in network transit and TLS handshakes.
The Auth Tax: Calling AWS Cognito for a token on every request is a "performance killer." A standard token exchange can take 150ms to 500ms+. Even with caching, the initial "cold" request will likely fail your 200ms target.
Azure Function Warm-up: If the Azure Function isn't on a Premium plan, "cold starts" can spike latency into the seconds. 
Reddit
Reddit
 +4
Recommended Adjustments
Relax Latency for P95: Consider moving the target to < 500ms or < 1s for the full end-to-end trip, or specify that the 200ms applies only to the GUID service's internal processing time, excluding network and auth overhead.
Token Caching Strategy: To meet high-speed NFRs, you must cache the Cognito token within the Azure Function (e.g., using a static variable or Redis) so you aren't calling AWS for a new token on every GUID request.
Availability (NFR-02): Your 99.9% target is standard, but remember your "availability" is now the product of three clouds. If Azure has 99.9% and AWS has 99.9%, your combined theoretical availability drops to roughly 99.8%. You may need a Failover strategy (as hinted in NFR-06) that is well-tested across these providers.

That changes the game significantly for the better! With token caching in the Azure Function, you eliminate the biggest "time thief" (the Cognito handshake) from the critical path.
However, there are still three specific areas where these NFRs might "rub" against your architecture:
1. The "Cold Start" vs. NFR-03 (Latency)
Even with a cached token, if your Azure Function is on a "Consumption Plan," a cold start can take 1–3 seconds.
The Conflict: A single cold start will immediately blow your < 200ms p95 target for that request.
The Fix: You’ll likely need the Azure Functions Premium plan (with "Always Ready" instances) or a frequent "warm-up" ping to keep the instance (and the cache) alive.
2. Multi-Hop Reliability (NFR-05)
You have a 99.99% Success Rate target (1 failure in 10,000).
The Conflict: You are daisy-chaining three distinct environments: Power Platform → Azure → AWS.
The Math: If each hop has 99.99% reliability, your end-to-end reliability is 


. You are mathematically "at risk" of missing NFR-05 simply due to the number of moving parts.
The Fix: Ensure your Custom Connector has a Retry Policy configured (e.g., 3 retries with exponential backoff) to mask transient network blips between clouds.
3. Burst Handling (NFR-01)
Your 10 TPS peak is modest, but Power Platform API Limits apply.
The Conflict: Power Apps/Power Automate have per-user request limits over a 24-hour window. If those 500 users are active simultaneously in other apps too, they might hit their Request Limits before they even reach your 10 TPS ceiling.
The Fix: Verify the Power Platform Request capacity for your specific licensing (Per User vs. Per App) to ensure it supports the burst.
Pro-Tip for NFR-06 (Recoverability):
Since you are using a Custom Connector, if the Azure Function goes down, the "failover" usually happens at the API Management (APIM) layer or via a secondary endpoint URL. Do you have a secondary region for the Azure Function, or is the "Failover" purely internal to the AWS side?

No worries at all—adding Azure Key Vault (AKV) and the "infrastructure vs. code" split adds two very specific "gotchas" to your NFRs.
Here is how those new details impact the plan:
1. The "First Request" Penalty (Latency vs. NFR-03)
Since you’re fetching the Client ID/Secret from Key Vault and then calling Cognito for a token, the very first request after a function restart is going to be incredibly slow.
The Chain: Function Wake up → AKV Call → Cognito Call → GUID Service.
The Risk: This "cold" path will likely take 1–2 seconds, easily blowing your 200ms p95 target if it happens frequently.
The Fix: Ensure your code fetches the secrets once and caches them in a static variable (alongside the token) so you don't hit Key Vault on every single GUID request.
2. The "Infrastructure" Gap (Recoverability vs. NFR-06)
Since you aren't using APIM (Azure API Management), your Custom Connector is likely pointing directly to a specific Azure Function URL.
The Reality Check: If that specific Azure Function region goes down, your "30-second recovery" (NFR-06) is likely impossible unless the infrastructure engineer has set up Azure Front Door or Traffic Manager to point to a backup function in a different region.
The Question for your Infra Peer: "If the Azure region hosting my function goes dark, does our Custom Connector automatically point somewhere else, or do we have to manually update the connector?"
3. Reliability "Hops" (NFR-05)
Your reliability chain just got longer: Power Platform → Azure Function → Azure Key Vault → AWS Cognito → AWS API Gateway → GUID Service.
With 6 components in the chain, achieving 99.99% (1 in 10,000 failure rate) is extremely difficult. A single blip in Key Vault or a networking hiccup between Azure and AWS will cause a failure.
Recommendation: You might want to suggest lowering NFR-05 (Reliability) to 99.9% to be more realistic for a multi-cloud, multi-service integration.
Quick Code Tip: Since you're the one writing the function code, are you using Managed Identity to talk to Key Vault? It’s much more reliable (and secure) than hardcoding credentials to get other credentials!

Since you're the one writing the function, switching from AWS Secrets Manager to Azure Key Vault (AKV) is actually a win for performance, provided you use Managed Identity.
Here’s how this setup specifically impacts your NFRs and a "pro-tip" for your code:
1. Latency & The "Double-Secret" Problem (NFR-03)
You now have a chain where the Custom Connector needs a secret to talk to the Function, which needs a secret to talk to Cognito.
The Risk: If your Function reaches out to AKV on every request to get the Cognito credentials, you will almost certainly miss that 200ms target.
The Context Fit: Your NFR-03 only "fits" if you implement Lazy Loading in your code. Fetch the Cognito Client ID/Secret from AKV once, store them in a static variable, and only fetch them again if the Function restarts.
2. Authentication Reliability (NFR-05)
Using Entra ID (Azure AD) OAuth for the Custom Connector is the "gold standard" for Power Platform. It’s highly reliable.
The Context Fit: This helps your 99.99% Reliability target because it’s a native "Microsoft-to-Microsoft" handshake. It's much more stable than passing API keys in headers.
3. The Best Way to Connect (Internal Tip)
Since your Infrastructure engineer is involved, ask them to enable a System-Assigned Managed Identity for your Azure Function.
Why this matters: You won't need another Client ID or Secret to talk to Key Vault. Your Function "is" its own identity.
Code Impact: You can use the DefaultAzureCredential class from the Azure Identity SDK. It’s cleaner, more secure, and faster than manual OAuth.
Updated "Reality Check" on the NFRs:
NFR	Status	Adjustment Needed?
Latency (<200ms)	⚠️ Risky	Possible only if secrets and tokens are cached in the Function's memory.
Throughput (10 TPS)	✅ Safe	Azure Functions and Key Vault handle 10 TPS without breaking a sweat.
Recovery (<30s)	❓ Unknown	Depends on whether your Infra Peer has a secondary "Warm" Function ready.
Does your current Function code already have a static class or variable set up to hold that Cognito token once it's fetched?
AI responses may include mistakes. Learn more




Yeah I've not looked at it in a while but I am certain it does cache the tokn
14 April 2026
That is a massive win for your Latency (NFR-03) and Reliability (NFR-05) targets. Since the "handshake" with AWS Cognito is the slowest part of your chain, caching that token in a static variable means 99% of your requests will skip that hop entirely.
To wrap up how these NFRs fit your specific Power Platform → Azure → AWS stack, here is the final "Developer's Reality Check":
1. Latency (NFR-03: < 200ms)
The "Fit": Tight, but achievable.
The "Gotcha": Your 95th percentile (p95) allows for 5% of requests to be slower. Those 5% will be your "Cold Starts" (when the Function wakes up) or "Cache Misses" (when the token expires).
Pro-Tip: If your p95 starts creeping over 200ms in testing, check if the Azure Function and the AWS API Gateway are in the same geographic region (e.g., UK South and London). Cross-region talk adds ~50ms of pure "travel time."
2. Reliability (NFR-05: 99.99%)
The "Fit": This is your biggest hurdle.
The "Gotcha": Even with caching, you are dependent on Azure Key Vault, Entra ID, and AWS API Gateway all being up simultaneously.
The Fix: Since you're writing the code, ensure you have a robust Try-Catch block around the GUID service call. If it fails, return a clean error so the Power Platform Custom Connector can trigger its built-in retry logic.
3. Accuracy (NFR-04: 100% Uniqueness)
The "Fit": Perfect.
The "Gotcha": This isn't actually on you or the Infra engineer—it’s on the AWS GUID service. As long as you aren't accidentally caching the result (the GUID itself) instead of the token, you’re golden.
The "Ask" for your Infra Peer:
Since you've got the code and caching handled, the only "missing link" for these NFRs is Recoverability (NFR-06). It’s worth asking them: "If the Azure Function region goes down, do we have a failover URL for the Custom Connector, or are we accepting a manual fix time?"