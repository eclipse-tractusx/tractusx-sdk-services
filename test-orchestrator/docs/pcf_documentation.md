# Product Carbon Footprint (PCF) Service Documentation

## 1. Overview

The Product Carbon Footprint (PCF) service provides a comprehensive set of API endpoints for validating and exchanging PCF (Product Carbon Footprint) data within the Catena-X ecosystem. This service orchestrates the complete PCF exchange workflow between suppliers and customers, including offer retrieval from Digital Twin Registry (DTR) and PCF data validation.

All endpoints are exposed under the following base prefix: `/productIds`

This prefix applies to every request mentioned below.

## 2. Key Features

- **PCF Offer Retrieval**: Fetch PCF submodel offers from supplier's Digital Twin Registry
- **Input Validation**: Comprehensive BPN and manufacturer part ID format validation
- **DTR Access Negotiation**: Automatic EDC-based access negotiation to supplier's DTR
- **Request Tracking**: Cache-based request tracking with configurable expiration
- **PCF Data Validation**: Validate incoming PCF updates against cached request data
- **Support for Multiple PCF Versions**: Support for PCF schema versions 7.0.0 and 8.0.0

All endpoints require authentication (`verify_auth`).

## 3. Core Concepts

### Business Partner Number (BPN) Format
BPNs follow the format: `BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}`
- `BPN` prefix
- One character: L (Location), S (Site), or A (Address)
- 10 alphanumeric characters
- 2 alphanumeric characters

Example: `BPNL000000000000`

### Manufacturer Part ID Format
Manufacturer part IDs can contain:
- Alphanumeric characters (A-Z, 0-9)
- Dashes (-)
- Underscores (_)

Example: `PART-12345-ABC`, `PART_456`

### Request ID
A UUID v4 identifier used to track PCF exchange requests and cache associated data.

## 4. API Endpoints

### GET `/productIds/{manufacturer_part_id}`

Retrieves a PCF offer from the supplier's Digital Twin Registry.

#### Purpose

This endpoint initiates the PCF exchange by:
1. Validating input parameters (BPN and manufacturer part ID)
2. Negotiating access to the supplier's DTR via EDC
3. Fetching the PCF submodel offer from the supplier's shell descriptor
4. Caching request metadata for later validation (if no request_id provided)
5. Verifying data retrieval capabilities by sending test GET requests

#### Request Parameters

| Parameter | Type | Location | Required | Default | Description |
|-----------|------|----------|----------|---------|-------------|
| `manufacturer_part_id` | string | Path | Yes | - | Manufacturer part identifier |
| `counter_party_id` | string | Query | Yes | - | Supplier's Business Partner Number |
| `counter_party_address` | string | Query | Yes | - | Supplier's EDC DSP endpoint URL |
| `pcf_version` | string | Query | No | `8.0.0` | PCF schema version (`7.0.0` or `8.0.0`) |
| `Edc-Bpn-L` | string | Header | Yes | - | Requester's Business Partner Number |
| `request_id` | string | Query | No | None | Optional request ID for existing requests |
| `timeout` | integer | Query | No | `80` | Request timeout in seconds |

#### Response (Success)

```json
{
  "status": "ok",
  "manufacturerPartId": "PART-12345-ABC",
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "offer": {
    "shell": {
      "id": "urn:uuid:shell-123",
      "submodelDescriptors": [...]
    },
    "pcf_submodel": {
      "semanticId": {
        "keys": [
          {
            "value": "urn:samm:io.catenax.pcf:8.0.0#ProductCarbonFootprint"
          }
        ]
      },
      "endpoints": [...]
    },
    "dataplane_url": "https://dataplane.example.com",
    "dtr_key": "api-key-123",
    "dct:type": {
      "@id": "cx-taxo:PcfExchange"
    }
  }
}
```

#### Response (Error Examples)

**Invalid BPN Format:**
```json
{
  "error": "REGEX_VALIDATION_FAILED",
  "message": "Invalid BPN: INVALID",
  "details": "Invalid format"
}
```

**No Shells Found in DTR:**
```json
{
  "error": "NO_SHELLS_FOUND",
  "message": "No shells found in DTR",
  "details": "No shell for manufacturerPartId: PART-12345-ABC"
}
```

**No PCF Submodel Found:**
```json
{
  "error": "NO_SHELLS_FOUND",
  "message": "No PCF submodel found",
  "details": "Shell exists but no PCF submodel descriptor"
}
```

**DTR Access Failed:**
```json
{
  "error": "CATALOG_FETCH_FAILED",
  "message": "DTR access negotiation failed",
  "details": "No dataplane URL or DTR key received"
}
```

---

### PUT `/productIds/{manufacturer_part_id}`

Validates incoming PCF data update from the supplier.

#### Purpose

This endpoint receives PCF data from the supplier and:
1. Validates input parameters (BPN and manufacturer part ID format)
2. Retrieves cached request data using the provided requestId
3. Verifies that the manufacturerPartId matches the cached data
4. Deletes the cache entry upon successful validation
5. Returns validation status

#### Request Parameters

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `manufacturer_part_id` | string | Path | Yes | Manufacturer part identifier |
| `requestId` | string | Query | Yes | Request ID from previous GET call |
| `Edc-Bpn` | string | Header | Yes | Supplier's Business Partner Number |

#### Response (Success)

```json
{
  "status": "ok",
  "message": "PCF data validated successfully",
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "manufacturerPartId": "PART-12345-ABC"
}
```

#### Response (Error Examples)

**Invalid BPN Format:**
```json
{
  "error": "REGEX_VALIDATION_FAILED",
  "message": "Invalid BPN format: INVALID",
  "details": "Expected format like BPNL000000000000"
}
```

**Request Not Found in Cache:**
```json
{
  "error": "NOT_FOUND",
  "message": "No cached request found for requestId: 550e8400-e29b-41d4-a716-446655440000",
  "details": "The requestId may have expired or is invalid"
}
```

**Manufacturer Part ID Mismatch:**
```json
{
  "error": "UNPROCESSABLE_ENTITY",
  "message": "ManufacturerPartId mismatch",
  "details": "Expected PART-999, got PART-12345-ABC"
}
```

**Invalid Characters in Part ID:**
```json
{
  "error": "REGEX_VALIDATION_FAILED",
  "message": "manufacturerPartId contains invalid characters",
  "details": "manufacturerPartId contains invalid characters"
}
```

## 5. Workflow

### Complete PCF Exchange Workflow

The typical PCF exchange follows this pattern:

#### Step 1: Initiate PCF Request (GET)

```bash
curl -X GET "http://localhost:8000/productIds/PART-12345-ABC" \
  -H "Edc-Bpn-L: BPNL000000000000" \
  -G \
  -d "counter_party_id=BPNL111111111111" \
  -d "counter_party_address=https://supplier.example.com/api/v1/dsp" \
  -d "pcf_version=8.0.0"
```

**Expected Response:**
```json
{
  "status": "ok",
  "manufacturerPartId": "PART-12345-ABC",
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "offer": { ... }
}
```

The system:
- Caches the request metadata with the `requestId`
- Cache expires after 1 hour (3600 seconds)
- Validates DTR access
- Confirms PCF submodel exists

#### Step 2: Send PCF Data (PUT)

```bash
curl -X PUT "http://localhost:8000/productIds/PART-12345-ABC" \
  -H "Edc-Bpn: BPNL111111111111" \
  -G \
  -d "requestId=550e8400-e29b-41d4-a716-446655440000"
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "PCF data validated successfully",
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "manufacturerPartId": "PART-12345-ABC"
}
```

The system:
- Validates the manufacturerPartId matches cached data
- Confirms requestId exists in cache
- Deletes cache entry (clean up)

### Using Existing Request ID

If re-using an existing request:

```bash
curl -X GET "http://localhost:8000/productIds/PART-12345-ABC" \
  -H "Edc-Bpn-L: BPNL000000000000" \
  -G \
  -d "counter_party_id=BPNL111111111111" \
  -d "counter_party_address=https://supplier.example.com/api/v1/dsp" \
  -d "request_id=550e8400-e29b-41d4-a716-446655440000"
```

When `request_id` is provided:
- The system skips caching
- Dummy PCF data is generated and sent via PUT request
- Request proceeds without cache-based validation

## 6. Utility Functions

The following functions (located in `test_orchestrator/utils/product_carbon_footprint.py`) implement the core PCF exchange logic.

### `validate_inputs(edc_bpn: str, manufacturer_part_id: str)`

Validates BPN and manufacturer part ID format.

**Checks Performed:**
- `edc_bpn` must not be empty
- `edc_bpn` must match format: `BPN[LSA][A-Z0-9]{10}[A-Z0-9]{2}`
- `manufacturer_part_id` (if provided) must contain only alphanumeric, dash, or underscore

**Raises:**
- `HTTPError` with code `MISSING_REQUIRED_FIELD` if BPN is missing
- `HTTPError` with code `REGEX_VALIDATION_FAILED` if format is invalid

### `fetch_pcf_offer_via_dtr(manufacturerPartId: str, dataplane_url: str, dtr_key: str, timeout: int = 10)`

Fetches PCF submodel offer from Digital Twin Registry.

**Process:**
1. Performs asset link lookup for manufacturerPartId
2. Retrieves shell ID(s)
3. Fetches shell descriptor
4. Searches for PCF submodel in descriptors
5. Returns offer details

**Returns:**
```json
{
  "shell": { ... },
  "pcf_submodel": { ... },
  "dataplane_url": "...",
  "dtr_key": "...",
  "dct:type": { "@id": "cx-taxo:PcfExchange" }
}
```

**Raises:**
- `HTTPError` with code `NO_SHELLS_FOUND` if no shells found
- `HTTPError` with code `TOO_MANY_ASSETS_FOUND` if multiple shells found
- `HTTPError` with code `NO_SHELLS_FOUND` if PCF submodel not found
- `HTTPError` with code `CATALOG_FETCH_FAILED` for other errors

### `send_pcf_responses(dataplane_url: str, dtr_key: str, product_id: str, request_id: str, bpn: str, timeout: int = 80)`

Sends PCF response requests (with and without requestId).

**Purpose:**
Verifies PCF data retrieval capabilities by making two test GET requests.

**Returns:**
```json
{
  "with_requestId": { ... },
  "without_requestId": { ... }
}
```

**Raises:**
- `HTTPError` with code `UNPROCESSABLE_ENTITY` if requests fail

### `send_pcf_put_request(counter_party_address: str, product_id: str, request_id: str, bpn: str, payload: Dict, timeout: int = 80)`

Sends PCF data via PUT request to counterparty.

**Parameters:**
- `counter_party_address`: Target endpoint URL
- `product_id`: Manufacturer part ID
- `request_id`: Request tracking identifier
- `bpn`: Business Partner Number
- `payload`: PCF data payload

**Returns:**
Response from the PUT request

### `pcf_check(manufacturer_part_id: str, counter_party_id: str, counter_party_address: str, pcf_version: str, edc_bpn_l: str, timeout: int, request_id: Optional[str] = None, cache: Optional[CacheProvider] = None, payload: Optional[Dict] = None)`

Main orchestration function for PCF exchange.

**Workflow:**
1. Validates inputs
2. Negotiates DTR access via EDC
3. Fetches PCF offer from DTR
4. If `request_id` is None:
   - Caches offer data (expires in 1 hour)
   - Sends GET requests to verify retrieval
5. If `request_id` exists:
   - Generates dummy PCF data
   - Sends PUT request with payload

**Returns:**
```json
{
  "status": "ok",
  "manufacturerPartId": "...",
  "requestId": "...",
  "offer": { ... }
}
```

**Raises:**
- `HTTPError` for validation, DTR access, or PCF submodel issues

### `validate_pcf_update(manufacturer_part_id: str, requestId: str, edc_bpn: str, cache: CacheProvider)`

Validates incoming PCF update request.

**Validation Steps:**
1. Checks BPN format
2. Checks manufacturer part ID format
3. Retrieves cached request data
4. Verifies manufacturerPartId matches cached data
5. Deletes cache entry upon success

**Returns:**
```json
{
  "status": "ok",
  "message": "PCF data validated successfully",
  "requestId": "...",
  "manufacturerPartId": "..."
}
```

**Raises:**
- `HTTPError` with code `REGEX_VALIDATION_FAILED` for invalid format
- `HTTPError` with code `NOT_FOUND` if requestId not in cache
- `HTTPError` with code `UNPROCESSABLE_ENTITY` if manufacturerPartId mismatch

### `delete_cache_entry(requestId: str, cache: CacheProvider)`

Deletes cache entry for a given request ID.

**Behavior:**
- Attempts to delete cache entry
- Logs warning if deletion fails
- Does not raise exceptions

## 7. Error Codes Reference

| Error Code | Status Code | Meaning | Common Cause |
|------------|-------------|---------|--------------|
| `MISSING_REQUIRED_FIELD` | 400 | Required field missing | Empty BPN |
| `REGEX_VALIDATION_FAILED` | 400 | Format validation failed | Invalid BPN or part ID format |
| `NO_SHELLS_FOUND` | 404 | Shell or PCF submodel not found | Part ID doesn't exist in DTR or no PCF submodel |
| `TOO_MANY_ASSETS_FOUND` | 400 | Multiple shells found | Ambiguous part ID in DTR |
| `CATALOG_FETCH_FAILED` | 502 | DTR access failed | EDC negotiation error or DTR unavailable |
| `NOT_FOUND` | 404 | Resource not found | RequestId expired or invalid |
| `UNPROCESSABLE_ENTITY` | 422 | Data validation failed | ManufacturerPartId mismatch or invalid characters |
| `UNKNOWN_ERROR` | 500 | Unexpected error | System error during validation |

## 8. Troubleshooting

### Common Issues

**Issue: "No shells found in DTR"**
- Verify manufacturerPartId exists in supplier's DTR
- Check if supplier's DTR contains assets with matching asset link
- Ensure counter_party_address is correct and accessible

**Issue: "DTR access negotiation failed"**
- Check counter_party_address is correct
- Verify EDC negotiation credentials are valid
- Ensure supplier's connector is running
- Check network connectivity

**Issue: "No PCF submodel found"**
- Verify the shell exists in DTR
- Check shell contains a submodel with PCF semantic ID
- Ensure PCF submodel descriptor is properly configured

**Issue: "ManufacturerPartId mismatch"**
- Verify requestId is for the same manufacturerPartId
- Check if cache entry has expired (default 1 hour)
- Regenerate request by calling GET again

**Issue: Cache entry not found**
- Check requestId is valid
- Verify cache server (Redis) is running
- Ensure cache entry hasn't expired (default 1 hour TTL)

## 9. Summary

The PCF service provides a complete, production-ready solution for PCF data exchange within Catena-X:

- **Comprehensive Validation**: Input validation and error handling
- **DTR Integration**: Seamless Digital Twin Registry access
- **Request Tracking**: Cache-based request management
- **Schema Support**: Multiple PCF schema versions
- **Error Handling**: Detailed error messages and codes
- **Testing**: Extensive test coverage

For questions or issues, please refer to the troubleshooting section or consult the test cases for usage examples.

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services