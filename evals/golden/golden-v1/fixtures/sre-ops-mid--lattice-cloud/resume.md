# Alex Chen

alex.chen@example.com | (555) 010-2200 | linkedin.com/in/example-alex

## Summary

Site Reliability Engineer with four years operating Kubernetes-based platforms in production. Strong incident-response habits and a preference for fixing systemic causes over patching symptoms. Comfortable in Python and Go.

## Experience

### Site Reliability Engineer — Holden Networks
*March 2023 – present*

- Owned reliability of the API edge for a B2B SaaS serving roughly 800 customer tenants on AWS EKS.
- Reduced control-plane error budget burn by tightening retry semantics in the ingress layer; rewrote the Envoy filter config and added a dashboard that on-call uses every shift.
- Authored Terraform modules for VPC peering and IAM role provisioning that the platform team adopted as the standard.
- Took on-call rotation roughly one week in four; led postmortems for two Sev-1 incidents and tracked action items to completion.
- Wrote a runbook library covering the top ten alert types; runbook usage cut MTTR for those alerts noticeably.

### Production Engineer — Stratford Analytics
*August 2021 – March 2023*

- Maintained the data ingestion pipeline (Kafka + Flink) for an analytics product used by internal sales teams.
- Migrated the monitoring stack from a SaaS APM to self-hosted Prometheus + Grafana, saving on the licensing line item and giving the team direct query access.
- Built a Slack bot in Python that posted incident timelines as they unfolded; on-call adopted it across the org.
- Mentored two interns through their first on-call shadow rotations.

## Education

**B.S. Computer Science** — State University, 2021

## Skills

Kubernetes, Prometheus, Grafana, Terraform, AWS (EKS, IAM, VPC, S3), Python, Go, Bash, Kafka, Envoy, distributed tracing, incident response, runbooks, on-call leadership.

## Side projects

- **kube-budget-cli** — open-source Go tool that reports namespace-level cost attribution from Kubernetes resource quotas. ~120 GitHub stars.
- Active reviewer on the Prometheus operator GitHub repo (12 merged PRs over 2024).
