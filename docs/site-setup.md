# Site setup: nam.theconvergencezone.com

Status 5 Nov 2026: the site is published in **preview** (robots.txt blocks crawlers) at
https://dzat3kduvlnwx.cloudfront.net/. The name waits on two DNS records at WordPress.com.

| Piece | Where | State |
|---|---|---|
| Bucket | s3://nam-recast-site-617711905691 (us-west-2, private, OAC) | done |
| CloudFront | E2Z8GL5ZGL3NHX, dzat3kduvlnwx.cloudfront.net, dir-index function, 404 page | done |
| Certificate | ACM us-east-1, e16b85e4-3ee3-482b-bd21-f6c57f8a9878 | pending validation CNAME |
| DNS | WordPress.com zone for theconvergencezone.com | Joe pastes two CNAMEs |
| Payments | Stripe Payment Link, $14.99/month | Joe creates the account |
| Grids | Cloudflare R2 | Joe creates the account; not started |

## Steps

1. **Certificate.** Add at WordPress.com (Upgrades > Domains > theconvergencezone.com > DNS records):
   `CNAME  _6b485fd647a90112262de51a52741780.nam  ->  _e8fccc70ab20e09f4f3327b268802c86.wzccmgtwzk.acm-validations.aws`.
   Re-run `bash deploy/08-site.sh` until it prints ISSUED and attaches the alias.
2. **Name.** Add `CNAME  nam  ->  dzat3kduvlnwx.cloudfront.net`. It replaces the wildcard that sends
   nam.* to the WordPress blog today.
3. **Publish.** `bash deploy/09-publish-site.sh` (preview) or `LAUNCH=1 bash deploy/09-publish-site.sh` (crawlers allowed).
4. **Stripe.** Account in Joe's name as a sole proprietor; product "FrankenNAM grids", $14.99/month recurring;
   a Payment Link; a coupon for the founding $9.99 rate (applied once the pledge of 20 is met). Paste the link
   into `site/pages/config.js` (STRIPE_PAYMENT_LINK). Keep the link unpublished, or the button hidden, until
   live verification has run 2-4 weeks. The webhook that issues access keys comes with the R2 step.
5. **R2.** Cloudflare account, bucket for the grids; separate small domain for the grid host recommended
   (the theconvergencezone.com zone stays at WordPress.com).
