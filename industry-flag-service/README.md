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

# Industry Flags Service (IFS)

## Introduction

The Industry Flags Service (IFS) is both a consumer and provider service, it enables users and systems to retrieve industry flag information.

This information can both be retrieved by the own company, visualizing what is available to be retrieved by customers, and also customers can access through the Eclipse Dataspace Connector (EDC) the same APIs by using a compatible Industry Flags Service application.

The application also includes a powerful library called "EDC Service" which is able to connect to applications/assets which are located behind the provider infrastructure. It enables applications that want to reuse the service in name of a specific company, to simply do "POST" and "GET" requests to these assets endpoints, by using the EDC proxy.

One of the objectives of the industry flags service is to understand how the EDC works and how can we optimize its usage, as an application behind it.

## Components
- Backend
- Frontend
- Two EDCs (consumer and provider connectors)


## Further Documentation

- [Architectural Documentation](./docs/architecture/README.md)
- [Frontend Component](./frontend/README.md)
- [Helm Chart](./charts/industry-flag-service)

