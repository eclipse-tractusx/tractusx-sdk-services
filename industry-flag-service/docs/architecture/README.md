<!--
#######################################################################

Tractus-X - Industry Flag Service 

Copyright (c) 2025 CGI Deutschland B.V. & Co. KG
Copyright (c) 2025 Contributors to the Eclipse Foundation

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This work is made available under the terms of the
Creative Commons Attribution 4.0 International (CC-BY-4.0) license,
which is available at
https://creativecommons.org/licenses/by/4.0/legalcode.

SPDX-License-Identifier: CC-BY-4.0

#######################################################################
-->

# Industry Flags Architecture Documentation

## Scope

The Industry Flags Service (IFS) is both a consumer and provider service, it enables users and systems to retrieve corporate industry information.

This information can both be retrieved by the own company, visualizing what is available to be retrieved by customers, and also customers can access through the Eclipse Dataspace Connector (EDC) the same APIs by using a compatible Industry Flags Service application.

The application also includes a powerful library called "EDC Service" which is able to connect to applications/assets which are located behind the provider infrastructure. It enables applications that want to reuse the service in name of a specific company, to simply do "POST" and "GET" requests to these assets endpoints, by using the EDC proxy.

One of the objectives of the industry flags service is to understand how the EDC works and how can we optimize its usage, as an application behind it.

## Context

This is the initial context:

![context](./resources/FlagManagmentContextProposal.png)



The industry flags service is located both in provider and consumer, but it will behave differently depending on the APIs called.

![tech-context](./resources/industry-flags-context.png)



## EDC Interaction

To ease the context from the application interaction with the EDC the following diagram was created:
![context2](./resources/EDC-Interaction-v9.drawio.png)

## EDC Service

The EDC Service is a library developed in Python that allows any application to interact in an optimized way with applications behind the EDC.

![context3](./resources/Architecture-EDC-Service-Library.drawio.png)

### Basic functionality

The simple functionality of the EDC Service is the following:

![simplified](./resources/simplified-context.png)

The first step is the connection that will be realized when a condition in the negotiation has changed:

* New policies were defined
* A different application wants to be connected
* The policy expiration has expired

Otherwise, the authentication information will be cached and reused for accessing the resources under the same condition.

Allowing application to communicate at least from one side really fast.

### Detailed Functionality

In the detailed functionality we can visualize the "white box" approach, where a negotiation is done by using the EDR interface of the EDC Connector.

![detailed](./resources/detailed-negotiation.png)

What will be stored is the EDR with the following parameters:

- Negotiation ID → So the complete cached EDR can always be requested
- Transfer ID → So that we can re-ask the authorization token to the EDC consumer every time.
- Data Plane URL → So the EDC we are communicating with is known.
- Asset and Creation Date → So the creation time and asset are known.
- Control Plane URL → So the service knows that this asset belongs to this EDC.

And the data exchange will be really fast and simple once the connection was established.
This connection will remain open until any of the conditions mentioned in the previous section are satisfied.

The connection takes approximately between 10 and 15 seconds.
Which is a limitation at the moment from the EDR interface at the EDC. Because the EDC Service needs to wait for the EDR token to appear in the EDC Cached EDR interface.


## System Components

### Backend Components Overview


![backend-components](./resources/backend-components.drawio.png)

#### Startup

To initializate the backend just run:

`py ./backend/init.py` or use the helm chart.

When started the backend will try to connect to the EDC consumer and the central idp from Catena-X if all the secrets and urls are correctly configured.

![alt text](./resources/startup-backend.png)

In case the connection with the EDC consumer fails, it will retry every 10 seconds.

### Frontend Components Overview

![frontend-components](./resources/frontend-components.drawio.png)
#### Startup

For starting the frontend run:

`cd ./frontend/industry-flag-service`
then
`npm install`
and then
`npm start`
`
or use a helm chart.

## EDC Configuration

### Asset

The asset `MUST` include the following configuration:
Changing just the url. The api key can also be changed.

```json
{
    "@id": "bcb534c4-2ff6-43f5-8271-7e0425dfb2fd",
    "@type": "Asset",
    "properties": {
        "dct:type": {
            "@id": "IndustryFlagService"
        },
        "name": "industry-flag-service",
        "id": "bcb534c4-2ff6-43f5-8271-7e0425dfb2fd"
    },
    "dataAddress": {
        "@type": "DataAddress",
        "type": "HttpData",
        "proxyPath": "true",
        "proxyMethod": "true",
        "proxyQueryParams": "true",
        "proxyBody": "true",
        "header:X-Api-Key": "ifs-api-key",
        "baseUrl": "https://ifs.app.url"
    },
    "@context": {
        "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
        "edc": "https://w3id.org/edc/v0.0.1/ns/",
        "tx": "https://w3id.org/tractusx/v0.0.1/ns/",
        "tx-auth": "https://w3id.org/tractusx/auth/",
        "cx-policy": "https://w3id.org/catenax/policy/",
        "odrl": "http://www.w3.org/ns/odrl/2/",
        "dct": "http://purl.org/dc/terms/",
        "cx-common": "https://w3id.org/catenax/ontology/common#",
        "cx-taxo": "https://w3id.org/catenax/taxonomy#"
    }
}
```

### Policy

There was defined a contraint in the policy that species that the usage is for the industry flag service application.


```json
{
        "@id": "flag-policy",
        "@type": "PolicyDefinition",
        "createdAt": 1731010627342,
        "policy": {
            "@id": "249e509d-8b3d-43c8-a447-cce4d265c27b",
            "@type": "odrl:Set",
            "odrl:permission": {
                "odrl:action": {
                    "@id": "odrl:use"
                },
                "odrl:constraint": {
                    "odrl:leftOperand": {
                        "@id": "cx-policy:UsagePurpose"
                    },
                    "odrl:operator": {
                        "@id": "odrl:eq"
                    },
                    "odrl:rightOperand": "catenax.industryflagservice"
                }
            },
            "odrl:prohibition": [],
            "odrl:obligation": []
        },
        "@context": {
            "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
            "edc": "https://w3id.org/edc/v0.0.1/ns/",
            "tx": "https://w3id.org/tractusx/v0.0.1/ns/",
            "tx-auth": "https://w3id.org/tractusx/auth/",
            "cx-policy": "https://w3id.org/catenax/policy/",
            "odrl": "http://www.w3.org/ns/odrl/2/"
        }
    }

```

### Contract

The contract can be defined in the following way, but the search will be done by DCT Type. When the catalog is requested.

 ```json
    {
        "@id": "4b752c20-7fd9-4706-975a-a8cec91ba0fd",
        "@type": "ContractDefinition",
        "accessPolicyId": "flag-policy",
        "contractPolicyId": "flag-policy",
        "assetsSelector": {
            "@type": "Criterion",
            "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
            "operator": "=",
            "operandRight": "12b86ea6-3365-4ca5-9b7e-c6d6cf8cdc55"
        },
        "@context": {
            "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
            "edc": "https://w3id.org/edc/v0.0.1/ns/",
            "tx": "https://w3id.org/tractusx/v0.0.1/ns/",
            "tx-auth": "https://w3id.org/tractusx/auth/",
            "cx-policy": "https://w3id.org/catenax/policy/",
            "odrl": "http://www.w3.org/ns/odrl/2/"
        }
    }

```


## Security

A security mechanism was implemented. There is the need to send in the authorization header `X-Api-Key` the api key which is configured in the charts here:

```yaml
authorization:
  enabled: true
  apiKey: 
    key: "X-Api-Key"
    value: ifs-api-key
```

The EDC will be sending this api key to the application in the provider side, so the api is still secured from external applications.


## API Documentation

The postman collection can be found [here](../postman/Industry%20Flag%20Service.postman_collection.json)

But here is the description of the apis:

| API | Method | Description | Request Example/Param | Response | API Key Required |
| :-- | --- | -- | -- | -- | :--: | 
| `/health` | `GET` | Confirms that the application is running | N/A | [Go to the response](#health-response) | |
| `/flags` | `GET` | This api returns the my company flags, the ones configured in the backend. | N/A | [Go to the response](#my-flags-response) | X |  
| `/flags/{id}` | `GET` | This api returns the proof from my flag. | Flag ID Param | [Go to the response](#my-flags-proof-response) | X |  
| `/flags/search` | `POST` | This api starts the search for the flags in the provider EDC. | `{"bpn":"BPNL000000000012"}` | [Go to the response](#flags-response) | X |  
| `/flags/proof` | `POST` | This api returns the proof of company flags from the provider EDC. | `{"bpn":"BPNL000000000012", "id": "414c8eff-9932-4c1f-9642-b0a1e2576751"}`| [Go to the response](#flags-proof-response) | X |  


### My Flags Response

```json
{
    "034d0d26-d448-4f7d-b92b-e2ae3d223fbf": {
        "industry": "chemicals",
        "type": "Boolean"
    },
    "cdbdae09-707b-43b5-91fe-04ad6438947b": {
        "industry": "automotive",
        "type": "Boolean"
    },
}
```

### Flags Response

The industry flag service will search in the `EDC Service` for the BPN and will query every `EDC` for the `dct:type` field in the catalog.

Once the negotiation is done the EDC service will be used to call the dataplane with the same interface as the current application.

The flags response shall be following the same structure as the `/flags` call. Because the EDC is calling it for us in the provider side.

In the provider side the BPN will appear in the logs when the information is requested, via the EDC.

![alt text](./resources/info.png)

### Flags Proof Response

This response will be the same as the `/flags/{id}` which the application calls behind the EDC though the proxy. Then the response which is received is proxied back to the response of the API.

## Flags Types


```yaml
flags:
  - industry: chemicals

  - industry: automotive
    mimetype: application/json
    proof: >
      {
        "result": true
      }
```

### Allowed Mimetypes

```json

{
  "application/json": ".json",
  "application/vc": ".jsonld",
  "application/ld+json": ".jsonld"
}
```

Files can't be uploaded directly, they need to be uploaded when the image is created. In case the mimetype is not a valid `json type`:

```json
[
    "application/json",
    "application/ld+json",
    "application/vc"
]
```

### Type

#### Boolean

The boolean flag is represented just by a flag `industry`.
No proof is attached, and the backend will just return a true value.

### Location/Proof

The proof that can be stored is the `JSON` payloads, because they will be parsed.

If no proof is specified and the mimetype is not `JSON` the backend will look for the file in the local when retrieving the proof.

The proofs and flags will be stored in a datamodel in memory, where the jsons are parsed into the object, and in case of the files the paths to the location are stored.

In the future there needs to be a api to upload the flags and proofs, like a "drag and drop" operation.

## Frontend Views

### Initial Draft

![ui-view](./resources/ui-view.png)

### Search View

The only thing that needs to be done is to introduce a valid BPN and then click the button to search.

![alt text](./resources/search.png)

If the user wants to see his flags he will click in "My Company Flags".

### My Company Flag View

The my company flag view allows the user to see which flags are registered.

![my-company-flag-view](./resources/mycompanyflag-view.png)

The user can also click in download to see the list of flags

![download-flags](./resources/download.png)

Booleans can't be downloaded, they are just a positive "flag" statement.

### Loading View

It will take the first time around 10 seconds to retreive the data, in case it is already loaded then the refresh will be done in less than `0,6s`, the same will apply for the download, that will be instantly.

![loading-flags](./resources/loading.png)

The first time the application searches for the flag in the EDC provider from the BPN partner and then if available displays the flag

### Error State

In case the flags are not able to be displayed it will display an error message:

![error-message](./resources/error.png)

This means that the backend is not available at the other side of the EDC.

### BPN Partner company flags View

![partner-company-flag-view](./resources/partner-company-flag-view.png)

The BPN number is used to search for the partner company flags from the provider EDC. If the the are flags available, it returns to the consumer EDC and displays them in the frontend.






