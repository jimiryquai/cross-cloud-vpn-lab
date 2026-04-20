Business Requirement & Architecture Overview

Power Platform cannot directly connect to the GUID service due to mTLS and certificate exchange requirements.
An Azure Function will act as an intermediary:
Power Platform → Azure Function
Azure Function → AWS GUID API Gateway
Objective is to avoid storing National Insurance numbers by securely calling the GUID service.
This is confirmed as an Inter-Cloud (Azure to AWS) connectivity requirement, not standard internet egress.
Connectivity Type

Traffic will originate from an existing Azure VNet.
Connectivity required from Azure VNet to AWS VPC hosting the GUID API Gateway.
This will use the CIA Inter-Cloud firewall stack, which is separate from the standard CIA egress service.
Inter-Cloud onboarding requires completion of the dedicated Inter-Cloud section within the CIA onboarding form.
 Encryption & Inspection Model

Traffic will use HTTPS with mutual TLS (mTLS) at the application layer.
End-to-end TLS is required.
As a result, decryption bypass will be required on the CIA Inter-Cloud firewalls.
Without bypass, full Layer 7 inspection would break mTLS.
Decryption bypass must be selected in the onboarding form and may require appropriate approval.
Firewall & Rule Requirements

For rule creation, the following must be provided:

Source CIDR ranges (Azure VNet)
Destination CIDR ranges (AWS side)
Destination URL
Confirmation DNS resolution works from Azure
Key differences from standard egress:

Inter-Cloud firewall rules are CIDR-based, not FQDN-based.
DNS resolution must be handled by the requester; the firewall does not perform DNS lookups.
Rules will allow traffic based strictly on source and destination IP ranges.
Traffic Flow & Routing

Confirmed high-level flow:

Azure VNet
Azure firewall
IPsec tunnel to AWS CIA Inter-Cloud firewall
AWS Transit Gateway
Target AWS VPC / API Gateway
Additional details:

IPsec tunnel bandwidth limit: ~1.25 Gbps
BGP is used for dynamic route propagation between AWS Transit Gateway and Azure route server.
On AWS side, no additional configuration required beyond default route to Transit Gateway.
zure side may require additional configuration; documentation will be shared.
No separate engagement with Cloud Connectivity is required at this stage.

VNet Considerations

Current plan is to use an existing Azure VNet (already configured for CIA egress).
There is ongoing discussion about potentially creating a new VNet.
If a new VNet is created, both Inter-Cloud and Egress onboarding may be required.
CIDR ranges must be confirmed before LLD production.
GUID Service Onboarding

The GUID service requires onboarding and API key issuance.
API key will be passed in request headers by the Azure Function.
There is a need to confirm whether formal engagement with Integration is required if the solution is not hosted directly on the CI platform.
Guidance documentation will be reviewed to ensure no onboarding step has been missed
Delivery Timeline & Process

Delivery timeline: 3–4 weeks (LLD + implementation).
LLD will be produced and reviewed internally prior to change implementation.
Once the change is raised:
Testing must occur within the 5-day change window.
Issues raised outside this window may require a new standard change.
Any blockers or slippage will be communicated promptly.
Outcome

Requirement confirmed as CIA Inter-Cloud (Azure to AWS) connectivity.
mTLS requires decryption bypass on Inter-Cloud firewalls.
CIDR-based firewall rules required (not FQDN-based).
Routing design clarified (IPsec + BGP propagation).
Onboarding form to be reviewed and updated with accurate CIDRs and endpoint details.
GUID service onboarding and integration confirmation to be validated.