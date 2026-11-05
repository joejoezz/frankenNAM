#!/usr/bin/env bash
# Public site for nam.theconvergencezone.com: private S3 bucket + Origin Access Control + CloudFront,
# an ACM certificate for the name, and the alias. Same pattern as ensplots deploy/06 + 09.
# Idempotent: re-run until it says done. DNS for theconvergencezone.com is at WordPress.com, so the two
# CNAMEs this needs (certificate validation, then the site) are pasted there by hand; the script prints them.
# Content goes up with deploy/09-publish-site.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
ACCOUNT=617711905691
REGION=us-west-2
NAME=nam-recast-site
BUCKET="$NAME-$ACCOUNT"
DOMAIN=${SITE_DOMAIN:-nam.theconvergencezone.com}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export AWS_DEFAULT_REGION=$REGION

echo "== bucket s3://$BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --create-bucket-configuration LocationConstraint=$REGION >/dev/null
  aws s3api put-bucket-tagging --bucket "$BUCKET" --tagging "TagSet=[{Key=project,Value=nam-recast}]"
  echo "  created"
fi
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "== origin access control"
OAC=$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='$NAME-oac'].Id | [0]" --output text)
if [ "$OAC" = "None" ] || [ -z "$OAC" ]; then
  OAC=$(aws cloudfront create-origin-access-control --origin-access-control-config \
    "Name=$NAME-oac,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query OriginAccessControl.Id --output text)
fi
echo "  $OAC"

echo "== directory-index function (/validation -> /validation.html, /maps/ -> /maps/index.html)"
FN="$NAME-dir-index"
cat > "$TMP/fn.js" <<'JS'
function handler(event) {
  var r = event.request;
  if (r.uri.endsWith('/')) r.uri += 'index.html';
  else if (!r.uri.includes('.')) r.uri += (r.uri === '/maps' ? '/index.html' : '.html');
  return r;
}
JS
if aws cloudfront describe-function --name "$FN" >/dev/null 2>&1; then
  ET=$(aws cloudfront describe-function --name "$FN" --query ETag --output text)
  aws cloudfront update-function --name "$FN" --if-match "$ET" --function-config "Comment=dir index,Runtime=cloudfront-js-2.0" --function-code "fileb://$TMP/fn.js" >/dev/null
else
  aws cloudfront create-function --name "$FN" --function-config "Comment=dir index,Runtime=cloudfront-js-2.0" --function-code "fileb://$TMP/fn.js" >/dev/null
fi
ET=$(aws cloudfront describe-function --name "$FN" --query ETag --output text)
aws cloudfront publish-function --name "$FN" --if-match "$ET" >/dev/null
FN_ARN=$(aws cloudfront describe-function --name "$FN" --stage LIVE --query FunctionSummary.FunctionMetadata.FunctionARN --output text)

echo "== distribution"
DIST=$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='$NAME'].Id | [0]" --output text)
if [ "$DIST" = "None" ] || [ -z "$DIST" ]; then
  cat > "$TMP/dist.json" <<JSON
{"CallerReference":"$NAME-$(date +%s)","Comment":"$NAME","Enabled":true,"DefaultRootObject":"index.html",
 "HttpVersion":"http2and3","IsIPV6Enabled":true,"PriceClass":"PriceClass_100",
 "Origins":{"Quantity":1,"Items":[{"Id":"s3","DomainName":"$BUCKET.s3.$REGION.amazonaws.com","OriginAccessControlId":"$OAC",
   "S3OriginConfig":{"OriginAccessIdentity":""}}]},
 "DefaultCacheBehavior":{"TargetOriginId":"s3","ViewerProtocolPolicy":"redirect-to-https","Compress":true,
   "AllowedMethods":{"Quantity":2,"Items":["GET","HEAD"],"CachedMethods":{"Quantity":2,"Items":["GET","HEAD"]}},
   "CachePolicyId":"658327ea-f89d-4fab-a63d-7e88639e58f6",
   "FunctionAssociations":{"Quantity":1,"Items":[{"FunctionARN":"$FN_ARN","EventType":"viewer-request"}]}},
 "CustomErrorResponses":{"Quantity":1,"Items":[{"ErrorCode":403,"ResponsePagePath":"/404.html","ResponseCode":"404","ErrorCachingMinTTL":60}]},
 "ViewerCertificate":{"CloudFrontDefaultCertificate":true}}
JSON
  DIST=$(aws cloudfront create-distribution --distribution-config "file://$TMP/dist.json" --query Distribution.Id --output text)
  aws cloudfront tag-resource --resource "arn:aws:cloudfront::$ACCOUNT:distribution/$DIST" --tags "Items=[{Key=project,Value=nam-recast}]"
  echo "  created $DIST"
else
  echo "  $DIST exists"
fi
CF=$(aws cloudfront get-distribution --id "$DIST" --query Distribution.DomainName --output text)
echo "$DIST $CF" > deploy/.site-dist

echo "== bucket policy: only this distribution may read"
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "$(cat <<JSON
{"Version":"2012-10-17","Statement":[{"Sid":"cloudfront","Effect":"Allow","Principal":{"Service":"cloudfront.amazonaws.com"},
 "Action":"s3:GetObject","Resource":"arn:aws:s3:::$BUCKET/*",
 "Condition":{"StringEquals":{"AWS:SourceArn":"arn:aws:cloudfront::$ACCOUNT:distribution/$DIST"}}}]}
JSON
)"
echo "  site is reachable at https://$CF/ once deploy/09 has published it"

echo "== certificate for $DOMAIN (us-east-1: CloudFront reads certificates from nowhere else)"
CERT=$(aws acm list-certificates --region us-east-1 --query "CertificateSummaryList[?DomainName=='$DOMAIN'].CertificateArn | [0]" --output text)
if [ "$CERT" = "None" ] || [ -z "$CERT" ]; then
  CERT=$(aws acm request-certificate --region us-east-1 --domain-name "$DOMAIN" --validation-method DNS \
    --tags Key=project,Value=nam-recast --query CertificateArn --output text)
  echo "  requested $CERT"; sleep 10
fi
STATUS=$(aws acm describe-certificate --region us-east-1 --certificate-arn "$CERT" --query Certificate.Status --output text)
if [ "$STATUS" != "ISSUED" ]; then
  read -r VNAME VVALUE < <(aws acm describe-certificate --region us-east-1 --certificate-arn "$CERT" \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord.[Name,Value]' --output text)
  cat <<EOF

  Certificate status: $STATUS. Add this record at WordPress.com
  (Upgrades > Domains > theconvergencezone.com > DNS records > Add record):

    Type:   CNAME
    Name:   ${VNAME%.theconvergencezone.com.}
    Value:  ${VVALUE%.}

  ACM usually issues within 5-30 minutes of the record going live. Re-run this script then.
EOF
  # match the ACM value itself: the domain's wildcard answers for every name
  if dig +short CNAME "$VNAME" @1.1.1.1 | grep -q "acm-validations.aws"; then
    echo "  The record is visible in public DNS; waiting for ACM (up to ~10 min)..."
    aws acm wait certificate-validated --region us-east-1 --certificate-arn "$CERT" 2>/dev/null || { echo "  not issued yet; re-run in a few minutes."; exit 0; }
  else
    exit 0
  fi
fi
echo "  ISSUED"

echo "== attaching $DOMAIN to $DIST"
aws cloudfront get-distribution-config --id "$DIST" > "$TMP/cf.json"
ET=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['ETag'])" "$TMP/cf.json")
CHANGED=$(python3 - "$TMP" "$DOMAIN" "$CERT" <<'PY'
import json, sys
tmp, domain, cert = sys.argv[1:4]
d = json.load(open(f"{tmp}/cf.json"))["DistributionConfig"]
items = set((d.get("Aliases") or {}).get("Items") or [])
if domain in items and d.get("ViewerCertificate", {}).get("ACMCertificateArn") == cert:
    print("no"); sys.exit()
items.add(domain)
d["Aliases"] = {"Quantity": len(items), "Items": sorted(items)}
d["ViewerCertificate"] = {"ACMCertificateArn": cert, "SSLSupportMethod": "sni-only",
                          "MinimumProtocolVersion": "TLSv1.2_2021", "CertificateSource": "acm"}
json.dump(d, open(f"{tmp}/cf-new.json", "w")); print("yes")
PY
)
if [ "$CHANGED" = "yes" ]; then
  aws cloudfront update-distribution --id "$DIST" --if-match "$ET" --distribution-config "file://$TMP/cf-new.json" >/dev/null
  echo "  alias + certificate set (CloudFront redeploys in a few minutes)"
else
  echo "  already attached"
fi
cat <<EOF

== last step, at WordPress.com: point the name at CloudFront

    Type:   CNAME
    Name:   ${DOMAIN%.theconvergencezone.com}
    Value:  $CF

  Then:  curl -sI https://$DOMAIN/ | head -1     (expect HTTP/2 200)
EOF
if dig +short CNAME "$DOMAIN" @1.1.1.1 | grep -q "$CF"; then echo "  DNS already points at CloudFront: done."; fi
