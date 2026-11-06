# Site setup: nam.theconvergencezone.com

Status 6 Nov 2026 (payments dropped, see docs/product-plan.md): the site is published in **preview** (robots.txt blocks crawlers) at
https://dzat3kduvlnwx.cloudfront.net/. The name waits on two DNS records at WordPress.com.

| Piece | Where | State |
|---|---|---|
| Bucket | s3://nam-recast-site-617711905691 (us-west-2, private, OAC) | done |
| CloudFront | E2Z8GL5ZGL3NHX, dzat3kduvlnwx.cloudfront.net, dir-index function, 404 page | done |
| Certificate | ACM us-east-1, e16b85e4-3ee3-482b-bd21-f6c57f8a9878 | pending validation CNAME |
| DNS | WordPress.com zone for theconvergencezone.com | Joe pastes two CNAMEs |
| Grids | `/grids/` in the site bucket, `deploy/12-publish-grids.sh` | Phase 0 case published (preview) |

## Steps

1. **Certificate.** Add at WordPress.com (Upgrades > Domains > theconvergencezone.com > DNS records):
   `CNAME  _6b485fd647a90112262de51a52741780.nam  ->  _e8fccc70ab20e09f4f3327b268802c86.wzccmgtwzk.acm-validations.aws`.
   Re-run `bash deploy/08-site.sh` until it prints ISSUED and attaches the alias.
2. **Name.** Add `CNAME  nam  ->  dzat3kduvlnwx.cloudfront.net`. It replaces the wildcard that sends
   nam.* to the WordPress blog today.
3. **Publish.** `bash deploy/09-publish-site.sh` (preview) or `LAUNCH=1 bash deploy/09-publish-site.sh` (crawlers allowed).
4. **Grids.** Free files under `/grids/` of the same bucket and CloudFront (no payments, no keys, no R2).
   `bash deploy/12-publish-grids.sh CASE...` copies `cases/<CASE>/products/` into `grids/` server-side and rebuilds the
   index pages; `deploy/09-publish-site.sh` never touches `grids/`. Cache is one day.
