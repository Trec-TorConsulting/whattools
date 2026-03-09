{{/*
Common labels
*/}}
{{- define "whattools.labels" -}}
app.kubernetes.io/part-of: whattools
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Selector labels for a component
*/}}
{{- define "whattools.selectorLabels" -}}
app: {{ .name }}
app.kubernetes.io/part-of: whattools
{{- end }}

{{/*
Full image name for a service
*/}}
{{- define "whattools.image" -}}
{{ .global.imageRegistry }}/{{ .name }}:{{ .global.imageTag }}
{{- end }}

{{/*
Security context for pods
*/}}
{{- define "whattools.securityContext" -}}
securityContext:
  runAsNonRoot: {{ .runAsNonRoot | default true }}
  runAsUser: {{ .runAsUser | default 1000 }}
  readOnlyRootFilesystem: {{ .readOnlyRootFilesystem | default true }}
  allowPrivilegeEscalation: {{ .allowPrivilegeEscalation | default false }}
  capabilities:
    drop:
      - ALL
{{- end }}

{{/*
Standard env vars from ConfigMap + Secrets
*/}}
{{- define "whattools.envFrom" -}}
envFrom:
  - configMapRef:
      name: whattools-config
{{- end }}

{{/*
Liveness probe
*/}}
{{- define "whattools.livenessProbe" -}}
livenessProbe:
  httpGet:
    path: {{ .path | default "/health" }}
    port: http
  initialDelaySeconds: {{ .initialDelaySeconds | default 15 }}
  periodSeconds: {{ .periodSeconds | default 10 }}
  timeoutSeconds: {{ .timeoutSeconds | default 5 }}
  failureThreshold: {{ .failureThreshold | default 3 }}
{{- end }}

{{/*
Readiness probe
*/}}
{{- define "whattools.readinessProbe" -}}
readinessProbe:
  httpGet:
    path: {{ .path | default "/ready" }}
    port: http
  initialDelaySeconds: {{ .initialDelaySeconds | default 10 }}
  periodSeconds: {{ .periodSeconds | default 5 }}
  timeoutSeconds: {{ .timeoutSeconds | default 3 }}
  failureThreshold: {{ .failureThreshold | default 3 }}
{{- end }}
