# Special Characteristics Service Documentation

The Special Characteristics service provides a set of API endpoints for validating Catena-X notification payloads, orchestrating data-transfer checks, and performing schema-based validation against Digital Twin Registry (DTR) data.

All endpoints are exposed under the following base prefix: `/test-cases/special-characteristics/v1`

This prefix applies to every request mentioned below.

## Overview

The service performs several validation and orchestration tasks:

- Structural validation of Catena-X notification payloads.
- Enforcement of event count limits.
- Retrieval of partner DTR shell descriptors based on Catena-X IDs.
- Digital Twin existence checks via the DT Pull Service.
- Schema validation of submodels based on semantic IDs.

All endpoints require authentication (`verify_auth`).


# Endpoints

## POST `/notification-validation/`

Validates the structure and content of a notification payload.

### Functionality
- Checks that the required sections (`header` and `content`) are present.
- Validates header fields such as UUIDs, timestamps, and BPN numbers.
- Ensures that the `listOfEvents` section is present and valid.
- Returns `{ "status": "ok" }` when validation succeeds.
- Raises `HTTPError` if any structural issue is detected.

### Expected Input
A Catena-X notification payload containing:
- `header` section
- `content` section with `information` and `listOfEvents`

### Response
```json
{ "status": "ok" }
```

## POST /data-transfer/

Orchestrates validation steps and checks if the Digital Twin referenced in the notification exists in the partner’s DTR.

### Functionality

1. Validates the notification payload structure.
2. Resolves the partner's DTR URL and token.
3. Fetches the Digital Twin shell descriptor for each event’s catenaXId.
4. Ensures all referenced Digital Twins exist.

### Parameters

- `counter_party_address`: Partner connector DSP address.
- `counter_party_id`: Partner identifier.
- `timeout`: External request timeout (default 80).
- `max_events`: Maximum allowed number of events (default 2).

### Response
```json
{ "message": "DT linkage & data transfer test is completed succesfully." }
```

Raises `HTTPError` if the DTR lookup fails or a referenced Digital Twin does not exist.

## POST /schema-validation/

Validates a notification payload and performs schema validation on the partner’s submodels.

### Functionality

1. Validates notification payload structure.
2. Retrieves DTR shell descriptors for all referenced Catena-X IDs.
3. For each event:
   - Extracts the submodel semantic ID.
   - Performs schema validation using the partner’s submodel definition.
4. Returns a summary containing validation results.

### Parameters

- `payload`: Notification payload.
- `counter_party_address`: Partner DSP endpoint.
- `counter_party_id`: Partner identifier.
- `timeout`: Timeout for external requests (default 80).
- `max_events`: Maximum number of allowed events (default 2).

### Response Example
```json
{
  "message": "Special Characteristics validation is completed.",
  "submodel_validation_message": [ ... ]
}
```

### Internal Logic and Utilities

The following functions (located in utils/special_characteristics.py) implement the validation logic used by all endpoints.

## `validate_notification_payload(payload: Dict)`

Validates the structure and required fields of a notification payload.

### Checks Performed

- `header` and `content` sections must exist.
- Required header fields: `messageId`, `context`, `sentDateTime`, `senderBpn`, `receiverBpn`, `expectedResponseBy`, `relatedMessageId`, `version`
- UUID format checks for IDs.
- Datetime format checks.
- BPN format checks.
- information and `listOfEvents` must exist in content.
- `listOfEvents` must be a non-empty list.
- Each event must contain: `eventType`, `catenaXId`, `submodelSemanticId`.
- Catena-X IDs must follow UUID format.

Raises `HTTPError` on any error.

### Returns:
```json
{ "status": "ok" }
```

## `validate_payload(payload: Dict, max_events: int)`

Performs lightweight validation:
- Checks event count (`listOfEvents` length).
- Returns `receiverBpn` and the list of events.

Raises `HTTPError` if the event limit is exceeded.

## `get_partner_dtr(counter_party_address, counter_party_id, timeout)`

Retrieves partner DTR access details:
- DTR shell endpoint URL.
- DTR token.

Raises `HTTPError` if the DTR endpoint is not found.

## `validate_events_in_dtr(events, dtr_url_shell, dtr_token, timeout)`

For each event:
- Performs a DTR lookup for the given Catena-X ID.
- Fetches the shell descriptor.
- Collects any errors during resolution.

Raises `HTTPError` if any Digital Twin is missing or cannot be retrieved.

Returns a list of shell descriptors.

## `process_notification_and_retrieve_dtr(...)`

Orchestration function used by the endpoint implementations.

Steps
- Validates event count via validate_payload.
- Retrieves partner DTR endpoint and token.
- Validates that each Digital Twin exists in the partner DTR.
- Returns the list of shell descriptors.

## `submodel_validation(counter_party_id, shell_descriptors_spec: Dict, semantic_id: str)`

Validates a submodel descriptor and its corresponding submodel data retrieved from the Digital Twin Registry (DTR).

This function is used to ensure that a submodel exists for a given semantic ID, the structure of the shell descriptor is correct, and the submodel data complies with the expected schema.

### Steps Performed

1. Verify that the shell descriptor contains at least one submodel descriptor.
2. Validate the shell descriptor structure against the expected schema.
3. Locate the submodel descriptor matching the provided semantic ID.
4. Retrieve submodel information and negotiate access to the partner’s DTR.
5. Fetch the submodel data from the href link provided in the descriptor.
6. Validate the retrieved submodel data against the schema corresponding to the semantic ID.

### Parameters

- `counter_party_id`: Identifier of the test subject operating the connector (BPNL until at least Catena-X Release 25.09).  
- `shell_descriptors_spec`: Dictionary containing shell descriptors returned by the DTR.  
- `semantic_id` (optional): Semantic ID of the submodel to validate. If not provided, the first semantic ID in the descriptor list is used.

### Returns

A dictionary containing the result of the submodel validation:

```json
{"status": "ok"}
```
or, in case of validation errors:

```json
{"status": "nok", "validation_errors": [...]}
```

### Error Handling
Raises `HTTPError` in the following cases:
- No submodel descriptors found in the DTR.
- Shell descriptor structure is invalid.
- Submodel descriptor for the semantic ID is not found.
- Unable to fetch submodel data from the DTR.
- Submodel response is not valid JSON.
- Submodel data does not conform to the expected schema.

### Notes
- This method is used by the `/schema-validation/` endpoint to validate each event's submodel.
- It depends on the `get_dtr_access` utility to gain access to the partner’s DTR.
- Uses `json_validator` to verify both shell descriptors and submodel data against their respective schemas.
- Ensures compliance with Catena-X and industry core specifications.

# Summary

The Special Characteristics service provides three main endpoints covering:
- Pure notification validation.
- Notification + Digital Twin lookup.
- Full schema validation against partner submodels.

All logic is centralised in the utils/special_characteristics.py module, ensuring consistent handling across use cases.

The service ensures that:
- The notification payload is structurally correct.
- Digital Twins referenced in events exist on the partner side.
- Submodels follow Catena-X schema requirements.

This documentation covers all endpoints and underlying logic required for integration and testing.