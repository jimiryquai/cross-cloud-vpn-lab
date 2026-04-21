User Stories & Dependencies

Currently, there are only 2 user stories being considered for the GUID integration. These are GUID-NINO (single lookup) and NINO-GUID (bulk import).

User Story 1: GUID-NINO (single lookup)

View a Single Record with Correct NINO Display

As an Assurance Officer

I want the system to show the correct NINO when I open a case

So that I can view the identifier that belongs to that specific record.

Acceptance Criteria

Given I open a case record
When the record is displayed
Then the system must use the record’s GUID to retrieve and display the matching NINO.
Given I have viewed a case record
When I open a different case record
Then the system must not show any NINO from the previous record (i.e., no “carry-over” from the last case).
Given a NINO is retrieved for viewing
When the system performs the retrieval
Then the system must record an audit entry containing the requestor identity and the GUID being processed.
 

User Story 2: NINO-GUID (bulk import)

Bulk Import with NINO-to-GUID Transformation

As a file uploader

I want to upload a file containing NINOs and have them converted into GUIDs in bulk

So that the import process can proceed using GUIDs rather than NINOs.

Acceptance Criteria

Given I upload a file containing NINOs
When the bulk import runs
Then the system must process the data in batches of up to 5,000 records.
Given a batch is processed
When the system performs the transformation
Then each NINO must be converted into its corresponding GUID.
Given a batch has been transformed
When results are returned to the import process
Then only the GUIDs must be provided for import.
Given the transformation has completed for submitted NINOs
When processing moves on
Then the system must discard the original NINOs immediately and must not retain them.