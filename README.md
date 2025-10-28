# tractusx-sdk-services
Test orchestrator &amp; DT Pull Service - Helps new partners in onboarding

These two services are both needed for the Testbed to work: both microservices needs to be up and running.
For more detailed documentation please visit each microservice's readme and docs.

### Local Kubernetes deployment

Helm is used in this project to ease Kubernetes deployment.

Deploy the microservices to Kubernetes with Helm
```sh
helm upgrade --install test_orchestrator ./charts/test_orchestrator --namespace default
helm upgrade --install dt-pull ./charts/dt-pull --namespace default --create-namespace
```
## Licenses

- [Apache-2.0](https://raw.githubusercontent.com/eclipse-tractusx/tractusx-sdk-services/main/LICENSE) for code
- [CC-BY-4.0](https://spdx.org/licenses/CC-BY-4.0.html) for non-code

## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 BMW AG
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services

