# industry-flag-service

![Version: 0.1.0](https://img.shields.io/badge/Version-0.1.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 1.16.0](https://img.shields.io/badge/AppVersion-1.16.0-informational?style=flat-square)

A Helm chart for Kubernetes

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` |  |
| autoscaling.enabled | bool | `false` |  |
| autoscaling.maxReplicas | int | `100` |  |
| autoscaling.minReplicas | int | `1` |  |
| autoscaling.targetCPUUtilizationPercentage | int | `80` |  |
| backend.affinity | object | `{}` |  |
| backend.authorization.apiKey.key | string | `"X-Api-Key"` |  |
| backend.authorization.apiKey.value | string | `"ifs-api-key"` |  |
| backend.authorization.enabled | bool | `true` |  |
| backend.autoscaling.enabled | bool | `false` |  |
| backend.autoscaling.maxReplicas | int | `100` |  |
| backend.autoscaling.minReplicas | int | `1` |  |
| backend.autoscaling.targetCPUUtilizationPercentage | int | `80` |  |
| backend.catenax.centralidp.clientid | string | `"sa328"` |  |
| backend.catenax.centralidp.clientsecret | string | `"hxcMhtYQew535JsQ53pm9MtOJdaPaOtj"` |  |
| backend.catenax.centralidp.realm | string | `"CX-Central"` |  |
| backend.catenax.centralidp.url | string | `"https://centralidp.beta.cofinity-x.com/auth/"` |  |
| backend.discovery.keys.edc_discovery | string | `"bpnl"` |  |
| backend.discovery.url | string | `"https://discoveryfinder.beta.cofinity-x.com/api/v1.0/administration/connectors/discovery/search"` |  |
| backend.edc.apiKey.key | string | `"X-Api-Key"` |  |
| backend.edc.apiKey.value | string | `"54F248FACF914D3B2A48FBC50C7CD8A78ADD726B9256310A773DD56A9059E7CC"` |  |
| backend.edc.apis.catalog | string | `"/management/v3/catalog/request"` |  |
| backend.edc.apis.dsp | string | `"/api/v1/dsp"` |  |
| backend.edc.apis.edr_prefix | string | `"/management/v2/edrs"` |  |
| backend.edc.apis.readiness | string | `"/api/check/readiness"` |  |
| backend.edc.apis.transfer_edr | string | `"/dataaddress?auto_refresh=true"` |  |
| backend.edc.apis.view_edr | string | `"/request"` |  |
| backend.edc.cache.expiration_time | int | `60` |  |
| backend.edc.dct_type_key | string | `"'http://purl.org/dc/terms/type'.'@id'"` |  |
| backend.edc.participantId | string | `"BPNL00000001VDGS"` |  |
| backend.edc.url | string | `"https://cgi-connector-edc.dataspaceos.preprod.cofinity-x.com"` |  |
| backend.enabled | bool | `true` |  |
| backend.flags[0].industry | string | `"chemicals"` |  |
| backend.flags[1].mimetype | string | `"application/json"` |  |
| backend.flags[1].industry | string | `"automotive"` |  |
| backend.flags[1].proof | string | `"{\n  \"result\": true\n}\n"` |  |
| backend.ifs.dct_type | string | `"IndustryFlagService"` |  |
| backend.ifs.policies | string | `"[\n  {\n    \"odrl:permission\": {\n        \"odrl:action\": {\n            \"@id\": \"odrl:use\"\n        },\n        \"odrl:constraint\": {\n          \"odrl:leftOperand\": {\n              \"@id\": \"cx-policy:UsagePurpose\"\n          },\n          \"odrl:operator\": {\n              \"@id\": \"odrl:eq\"\n          },\n          \"odrl:rightOperand\": \"catenax.industryflagservice\"\n      }\n    },\n    \"odrl:prohibition\": [],\n    \"odrl:obligation\": []\n  }\n]\n"` |  |
| backend.ifs.refresh_interval | int | `1440` |  |
| backend.image.pullPolicy | string | `"Always"` |  |
| backend.image.repository | string | `"cxmihgs2e4956.azurecr.io/industry-flag-service-backend"` |  |
| backend.image.tag | string | `"latest"` |  |
| backend.imagePullSecrets | list | `[{"name":"acr-pull-secret"}]` | Existing image pull secret to use to [obtain the container image from private registries](https://kubernetes.io/docs/concepts/containers/images/#using-a-private-registry) |
| backend.ingress.annotations."nginx.ingress.kubernetes.io/backend-protocol" | string | `"HTTP"` |  |
| backend.ingress.annotations."nginx.ingress.kubernetes.io/force-ssl-redirect" | string | `"true"` |  |
| backend.ingress.annotations."nginx.ingress.kubernetes.io/ssl-passthrough" | string | `"false"` |  |
| backend.ingress.className | string | `"nginx"` |  |
| backend.ingress.enabled | bool | `true` |  |
| backend.ingress.hosts[0].host | string | `"TODO__XXX__YOUR_VALUE___XXX"` |  |
| backend.ingress.hosts[0].paths[0].path | string | `"/flags"` |  |
| backend.ingress.hosts[0].paths[0].pathType | string | `"Prefix"` |  |
| backend.ingress.hosts[0].paths[1].path | string | `"/health"` |  |
| backend.ingress.hosts[0].paths[1].pathType | string | `"Prefix"` |  |
| backend.ingress.ingressClassName | string | `"nginx"` |  |
| backend.ingress.tls[0].hosts[0] | string | `"TODO__XXX__YOUR_VALUE___XXX"` |  |
| backend.ingress.tls[0].secretName | string | `"default-ssl-certificate"` |  |
| backend.name | string | `"ifs-backend"` |  |
| backend.nodeSelector | object | `{}` |  |
| backend.podAnnotations | object | `{}` |  |
| backend.podSecurityContext.fsGroup | int | `3000` | The owner for volumes and any files created within volumes will belong to this guid |
| backend.podSecurityContext.runAsGroup | int | `3000` | Processes within a pod will belong to this guid |
| backend.podSecurityContext.runAsUser | int | `1000` | Runs all processes within a pod with a special uid |
| backend.podSecurityContext.seccompProfile.type | string | `"RuntimeDefault"` | Restrict a Container's Syscalls with seccomp |
| backend.replicaCount | int | `1` |  |
| backend.resources | object | `{}` |  |
| backend.securityContext.allowPrivilegeEscalation | bool | `false` | Controls [Privilege Escalation](https://kubernetes.io/docs/concepts/security/pod-security-policy/#privilege-escalation) enabling setuid binaries changing the effective user ID |
| backend.securityContext.capabilities.add | list | `[]` | Specifies which capabilities to add to issue specialized syscalls |
| backend.securityContext.capabilities.drop | list | `["ALL"]` | Specifies which capabilities to drop to reduce syscall attack surface |
| backend.securityContext.readOnlyRootFilesystem | bool | `true` | Whether the root filesystem is mounted in read-only mode |
| backend.securityContext.runAsGroup | int | `3000` | The owner for volumes and any files created within volumes will belong to this guid |
| backend.securityContext.runAsNonRoot | bool | `true` | Requires the container to run without root privileges |
| backend.securityContext.runAsUser | int | `1000` | The container's process will run with the specified uid |
| backend.service.port | int | `8000` |  |
| backend.service.type | string | `"ClusterIP"` |  |
| backend.startup.checks | bool | `false` |  |
| backend.startup.refresh_interval | int | `10` |  |
| backend.tolerations | list | `[]` |  |
| backend.volumeMounts | list | `[{"mountPath":"/backend/config","name":"ifs-backend-config"},{"mountPath":"/backend/data","name":"pvc-ifs-backend","subPath":"data"},{"mountPath":"/backend/logs","name":"tmpfs","subPath":"logs"}]` | specifies the volume mounts for the backend deployment |
| backend.volumeMounts[0] | object | `{"mountPath":"/backend/config","name":"ifs-backend-config"}` | mounted path for the backend configuration added in the config maps |
| backend.volumeMounts[1] | object | `{"mountPath":"/backend/data","name":"pvc-ifs-backend","subPath":"data"}` | contains the location for the process data directory |
| backend.volumeMounts[2] | object | `{"mountPath":"/backend/logs","name":"tmpfs","subPath":"logs"}` | contains the log directory uses by the backend |
| backend.volumes | list | `[{"configMap":{"name":"{{ .Release.Name }}-ifs-backend-config"},"name":"ifs-backend-config"},{"name":"pvc-ifs-backend","persistentVolumeClaim":{"claimName":"{{ .Release.Name }}-pvc-ifs-backend-data"}},{"emptyDir":{},"name":"tmpfs"},{"csi":{"driver":"secrets-store.csi.k8s.io","readOnly":true,"volumeAttributes":{"secretProviderClass":"secrets-provider"}},"name":"secrets-store"}]` | volume claims for the containers |
| backend.volumes[0] | object | `{"configMap":{"name":"{{ .Release.Name }}-ifs-backend-config"},"name":"ifs-backend-config"}` | persist the backend configuration |
| backend.volumes[1] | object | `{"name":"pvc-ifs-backend","persistentVolumeClaim":{"claimName":"{{ .Release.Name }}-pvc-ifs-backend-data"}}` | persist the backend data directories |
| backend.volumes[2] | object | `{"emptyDir":{},"name":"tmpfs"}` | temporary file system mount |
| frontend.configuration.apiKey | string | `"ifs-api-key"` |  |
| frontend.configuration.backendUrl | string | `"TODO__XXX__YOUR_VALUE___XXX"` |  |
| frontend.configuration.endpoints.GetCompanyFlagProof | string | `"/flags/proof"` |  |
| frontend.configuration.endpoints.getMyFlagProof | string | `"/flags"` |  |
| frontend.configuration.endpoints.getMyFlags | string | `"/flags"` |  |
| frontend.configuration.endpoints.searchCompanyFlags | string | `"flags/search"` |  |
| frontend.enabled | bool | `true` |  |
| frontend.image.pullPolicy | string | `"Always"` |  |
| frontend.image.repository | string | `"TODO__XXX__YOUR_VALUE___XXX/industry-flag-service-frontend"` |  |
| frontend.image.tag | string | `"latest"` |  |
| frontend.imagePullSecrets[0].name | string | `"acr-pull-secret"` |  |
| frontend.ingress.annotations."nginx.ingress.kubernetes.io/backend-protocol" | string | `"HTTP"` |  |
| frontend.ingress.annotations."nginx.ingress.kubernetes.io/force-ssl-redirect" | string | `"true"` |  |
| frontend.ingress.annotations."nginx.ingress.kubernetes.io/service-upstream" | string | `"true"` |  |
| frontend.ingress.annotations."nginx.ingress.kubernetes.io/ssl-passthrough" | string | `"false"` |  |
| frontend.ingress.className | string | `"nginx"` |  |
| frontend.ingress.enabled | bool | `true` |  |
| frontend.ingress.hosts[0].host | string | `"TODO__XXX__YOUR_VALUE___XXX"` |  |
| frontend.ingress.hosts[0].paths[0].path | string | `"/"` |  |
| frontend.ingress.hosts[0].paths[0].pathType | string | `"Prefix"` |  |
| frontend.ingress.ingressClassName | string | `"nginx"` |  |
| frontend.ingress.tls[0].hosts[0] | string | `"TODO__XXX__YOUR_VALUE___XXX"` |  |
| frontend.ingress.tls[0].secretName | string | `"default-ssl-certificate"` |  |
| frontend.livenessProbe | string | `nil` |  |
| frontend.name | string | `"ifs-frontend"` |  |
| frontend.readinessProbe | string | `nil` |  |
| frontend.replicaCount | int | `1` |  |
| frontend.resources | object | `{}` |  |
| frontend.service.port | int | `8080` |  |
| frontend.service.type | string | `"ClusterIP"` |  |
| frontend.volumeMounts | list | `[]` |  |
| frontend.volumes | list | `[]` |  |
| fullnameOverride | string | `""` |  |
| name | string | `"industry-flag-service"` |  |
| nameOverride | string | `""` |  |
| nodeSelector | object | `{}` |  |
| podAnnotations | object | `{}` |  |
| podLabels | object | `{}` |  |
| podSecurityContext | object | `{}` |  |
| securityContext | object | `{}` |  |
| serviceAccount.annotations | object | `{}` |  |
| serviceAccount.automount | bool | `true` |  |
| serviceAccount.create | bool | `true` |  |
| serviceAccount.name | string | `""` |  |
| tolerations | list | `[]` |  |
| volumeMounts | list | `[]` |  |
| volumes[0].csi.driver | string | `"secrets-store.csi.k8s.io"` |  |
| volumes[0].csi.readOnly | bool | `true` |  |
| volumes[0].csi.volumeAttributes.secretProviderClass | string | `"secrets-provider"` |  |
| volumes[0].name | string | `"secrets-store"` |  |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.11.0](https://github.com/norwoodj/helm-docs/releases/v1.11.0)



## NOTICE

This work is licensed under the [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode).

- SPDX-License-Identifier: CC-BY-4.0
- SPDX-FileCopyrightText: 2025 Contributors to the Eclipse Foundation
- Source URL: https://github.com/eclipse-tractusx/tractusx-sdk-services