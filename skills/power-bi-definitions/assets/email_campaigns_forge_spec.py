"""Example pbip-model-forge spec: email campaign performance (Mailchimp / Klaviyo / Brevo style).

Grain: one row per campaign send to one segment.
Answers: which campaigns earn revenue, where the send funnel leaks
(sent -> delivered -> opened -> clicked -> ordered), and which segments are
eroding (unsubscribes, bounces).

Build:  uvx --from git+https://github.com/C-Kapsalis/pbip-model-forge@v1.1.0 pbip-forge build email_campaigns.py out/EmailCampaigns --check --profile handoff
Gate:   uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight check out/EmailCampaigns
"""

import datetime as dt

SPEC = {
    "name": "EmailCampaigns",
    "tables": [
        {
            "name": "Campaigns",
            "description": "One row per email campaign or automated flow.",
            "columns": [
                {"name": "campaign_id", "type": "int64", "key": True},
                {"name": "campaign_name", "type": "string",
                 "description": "Campaign name as it appears in the email platform."},
                {"name": "campaign_type", "type": "string",
                 "description": "Newsletter, Promotion or Automation."},
                {"name": "offer", "type": "string",
                 "description": "Headline offer in the email, or None."},
                {"name": "subject_line", "type": "string",
                 "description": "Subject line of the winning variant."},
            ],
            "rows": [
                [1, "January Newsletter", "Newsletter", "None", "What we roasted in January"],
                [2, "Winter Sale", "Promotion", "20% off", "20% off every winter blend, 3 days only"],
                [3, "Welcome Flow", "Automation", "10% first order", "Welcome in. Here is 10% for your first bag"],
                [4, "Spring Launch", "Promotion", "Free shipping", "Spring single-origins are here"],
                [5, "Win-back Flow", "Automation", "15% comeback", "We miss you. 15% to come back"],
            ],
        },
        {
            "name": "Segments",
            "description": "Audience segment a campaign was sent to.",
            "columns": [
                {"name": "segment_id", "type": "int64", "key": True},
                {"name": "segment_name", "type": "string",
                 "description": "Segment name in the email platform."},
                {"name": "lifecycle_stage", "type": "string",
                 "description": "Lifecycle stage: Prospect, Active, Lapsed."},
                {"name": "acquisition_source", "type": "string",
                 "description": "Where most of the segment signed up."},
            ],
            "rows": [
                [1, "Newsletter subscribers", "Prospect", "Website pop-up"],
                [2, "Active customers", "Active", "Checkout opt-in"],
                [3, "Lapsed 180d+", "Lapsed", "Checkout opt-in"],
                [4, "VIP repeat buyers", "Active", "Checkout opt-in"],
            ],
        },
        {
            "name": "CampaignSends",
            "description": "One row per campaign send to one segment. Core fact.",
            "hidden": True,
            "columns": [
                {"name": "send_id", "type": "int64"},
                {"name": "send_date", "type": "datetime", "format": "General Date"},
                {"name": "campaign_id", "type": "int64"},
                {"name": "segment_id", "type": "int64"},
                {"name": "sent", "type": "int64", "summarizeBy": "sum"},
                {"name": "delivered", "type": "int64", "summarizeBy": "sum"},
                {"name": "unique_opens", "type": "int64", "summarizeBy": "sum"},
                {"name": "unique_clicks", "type": "int64", "summarizeBy": "sum"},
                {"name": "unsubscribes", "type": "int64", "summarizeBy": "sum"},
                {"name": "orders", "type": "int64", "summarizeBy": "sum"},
                {"name": "revenue", "type": "double", "summarizeBy": "sum",
                 "format": "$ #,0.00"},
            ],
            "rows": [
                [101, dt.date(2025, 1, 9),  1, 1, 12400, 12150, 4610, 362, 41,  18,  702.00],
                [102, dt.date(2025, 1, 9),  1, 2,  5200,  5150, 2420, 288, 9,   41, 1681.00],
                [103, dt.date(2025, 1, 23), 2, 2,  5180,  5120, 2610, 512, 14, 133, 5187.00],
                [104, dt.date(2025, 1, 23), 2, 4,   820,   818,  560, 141, 1,   52, 2444.00],
                [105, dt.date(2025, 1, 23), 2, 3,  3900,  3610,  790,  61, 38,  11,  418.00],
                [106, dt.date(2025, 2, 1),  3, 1,  1350,  1338,  842, 166, 6,   39, 1287.00],
                [107, dt.date(2025, 2, 13), 1, 1, 12900, 12610, 4390, 330, 52,  15,  585.00],
                [108, dt.date(2025, 2, 13), 1, 2,  5310,  5260, 2390, 270, 11,  37, 1517.00],
                [109, dt.date(2025, 3, 1),  3, 1,  1480,  1466,  901, 171, 5,   44, 1452.00],
                [110, dt.date(2025, 3, 6),  5, 3,  3870,  3540,  702,  88, 44,  19,  722.00],
                [111, dt.date(2025, 3, 20), 4, 2,  5400,  5340, 2290, 341, 10,  71, 2911.00],
                [112, dt.date(2025, 3, 20), 4, 4,   845,   843,  571, 152, 0,   49, 2401.00],
                [113, dt.date(2025, 3, 20), 4, 1, 13300, 12980, 3950, 298, 61,  22,  880.00],
                [114, dt.date(2025, 4, 1),  3, 1,  1520,  1505,  930, 175, 7,   46, 1518.00],
            ],
        },
    ],
    "calendar": {"name": "__Calendar"},
    "measures_table": {
        "name": "Email Measures",
        "description": "Measure home table for the email send funnel and revenue.",
        "measures": [
            {"name": "Total Sent", "expression": "SUM(CampaignSends[sent])",
             "format": "#,0", "description": "Emails sent, before bounces."},
            {"name": "Total Delivered", "expression": "SUM(CampaignSends[delivered])",
             "format": "#,0", "description": "Emails accepted by the receiving server."},
            {"name": "Total Unique Opens", "expression": "SUM(CampaignSends[unique_opens])",
             "format": "#,0", "description": "Recipients who opened at least once."},
            {"name": "Total Unique Clicks", "expression": "SUM(CampaignSends[unique_clicks])",
             "format": "#,0", "description": "Recipients who clicked at least once."},
            {"name": "Total Unsubscribes", "expression": "SUM(CampaignSends[unsubscribes])",
             "format": "#,0", "description": "Recipients who unsubscribed from the send."},
            {"name": "Total Orders", "expression": "SUM(CampaignSends[orders])",
             "format": "#,0", "description": "Orders attributed to the send by the platform."},
            {"name": "Total Revenue", "expression": "SUM(CampaignSends[revenue])",
             "format": "$ #,0.00", "description": "Revenue attributed to the send by the platform."},
            {"name": "Delivery %", "expression": "DIVIDE([Total Delivered], [Total Sent])",
             "format": "0.0%", "description": "Share of sent emails that were delivered."},
            {"name": "Open %", "expression": "DIVIDE([Total Unique Opens], [Total Delivered])",
             "format": "0.0%",
             "description": "Unique opens over delivered. Inflated by privacy-protected opens."},
            {"name": "CTR %", "expression": "DIVIDE([Total Unique Clicks], [Total Delivered])",
             "format": "0.0%", "description": "Unique clicks over delivered emails."},
            {"name": "CTOR %", "expression": "DIVIDE([Total Unique Clicks], [Total Unique Opens])",
             "format": "0.0%", "description": "Unique clicks over unique opens: content pull."},
            {"name": "Unsubscribe %", "expression": "DIVIDE([Total Unsubscribes], [Total Delivered])",
             "format": "0.00%", "description": "Unsubscribes over delivered emails."},
            {"name": "Click to Order %", "expression": "DIVIDE([Total Orders], [Total Unique Clicks])",
             "format": "0.0%", "description": "Orders over unique clicks: landing and offer pull."},
            {"name": "Revenue per Recipient",
             "expression": "DIVIDE([Total Revenue], [Total Delivered])",
             "format": "$ #,0.000", "description": "Revenue per delivered email."},
            {"name": "Sends #", "expression": "DISTINCTCOUNT(CampaignSends[send_id])",
             "format": "#,0", "description": "Number of campaign-to-segment sends."},
        ],
    },
    "relationships": [
        {"from": "CampaignSends.campaign_id", "to": "Campaigns.campaign_id"},
        {"from": "CampaignSends.segment_id", "to": "Segments.segment_id"},
        {"from": "CampaignSends.send_date", "to": "__Calendar.Date"},
    ],
}
