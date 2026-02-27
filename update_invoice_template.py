import sqlite3

html = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Invoice {{invoice_number}}</title>
  <!-- Google Font: Smooch Sans -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Smooch+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root{
      --ink:#111;
      --muted:#666;
      --line:#d9d9d9;
      --paper:#fff;
      --banner:#0b0b0b;
      --accent:#000;
    }

    /* Page / print */
    @page { size: A4; margin: 18mm; }
    *{ box-sizing:border-box; }
    body{
      margin:0;
      background:#f2f3f5;
      font-family: 'Smooch Sans', Arial, Helvetica, sans-serif;
      color:var(--ink);
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .sheet{
      width: 210mm;
      min-height: 297mm;
      margin: 16px auto;
      background: var(--paper);
      box-shadow: 0 10px 30px rgba(0,0,0,.08);
      padding: 0;
    }
    .content{
      padding: 18mm;
    }

    /* Banner */
    .banner{
      background: var(--banner);
      color: #fff;
      padding: 22mm 18mm;
      display:flex;
      align-items:flex-end;
      justify-content:space-between;
    }
    .brand{
      line-height:1;
    }
    .brand .name{
      font-size: 44px;
      letter-spacing: 2px;
      font-weight: 700;
    }
    .brand .tag{
      font-size: 20px;
      opacity: .9;
      margin-top: 6px;
      letter-spacing: .4px;
    }
    .banner .doc-type{
      font-size: 28px;
      font-weight: 600;
      opacity: .95;
    }

    /* Top area */
    .top{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 18mm;
      margin-top: 14mm;
      align-items:start;
    }

    .addr-box{
      border: 2px solid var(--line);
      padding: 12mm 10mm;
      width: 78%;
      min-height: 45mm;
    }
    .addr-box .to{
      font-weight:700;
      margin-bottom: 6px;
    }
    .addr-box .line{
      margin: 2px 0;
      font-weight:600;
    }

    .meta{
      justify-self:end;
      width: 100%;
      max-width: 80mm;
    }
    .meta-row{
      display:flex;
      justify-content:space-between;
      gap: 8mm;
      padding: 3px 0;
      font-size: 14px;
    }
    .meta-row .label{ color: var(--muted); }
    .meta-row .value{ font-weight:700; }
    .meta .ref{
      margin-top: 8px;
      padding-top: 8px;
    }
    .meta .ref .value{
      font-weight:700;
    }

    /* Section header line */
    .section-head{
      margin-top: 16mm;
      display:flex;
      align-items:flex-end;
      justify-content:space-between;
      gap: 10mm;
      padding-bottom: 6px;
      border-bottom: 2px solid var(--line);
      font-weight:700;
    }
    .section-head .right{
      min-width: 20mm;
      text-align:right;
    }

    /* Services table */
    table{
      width:100%;
      border-collapse:collapse;
      margin-top: 6mm;
    }
    td, th{
      padding: 10px 0;
      vertical-align:top;
      font-size: 14px;
    }
    .services td.desc{
      padding-right: 10mm;
    }
    .services td.amt{
      text-align:right;
      white-space:nowrap;
      font-variant-numeric: tabular-nums;
    }
    .services tr + tr td{
      border-top: 1px solid #efefef;
    }

    /* Bottom area */
    .bottom{
      display:grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 18mm;
      margin-top: 14mm;
      align-items:start;
    }

    .terms{
      border-top: 2px solid var(--line);
      padding-top: 10mm;
    }
    .terms .due{
      font-weight:700;
      margin-bottom: 8mm;
    }
    .bank{
      color: var(--muted);
      font-size: 13px;
      line-height:1.6;
    }
    .bank strong{
      color: var(--ink);
      font-weight:700;
    }
    .bank .label{
      display:inline-block;
      min-width: 38mm;
      color: var(--muted);
    }

    .totals{
      border-top: 2px solid var(--line);
      padding-top: 10mm;
      font-size: 14px;
      width: 100%;
      justify-self:end;
      max-width: 80mm;
    }
    .totals .row{
      display:flex;
      justify-content:space-between;
      gap: 10mm;
      padding: 6px 0;
      font-variant-numeric: tabular-nums;
    }
    .totals .row .label{ color: var(--muted); }
    .totals .row .value{ font-weight:700; }
    .totals .row.total{
      margin-top: 6px;
      padding-top: 10px;
      border-top: 2px solid var(--line);
      font-size: 16px;
    }
    .totals .row.total .label{ color: var(--ink); font-weight:700; }
    .totals .row.total .value{ font-weight:800; }

    /* Footer */
    .footer{
      margin-top: 22mm;
      padding-top: 10mm;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 11.5px;
      line-height:1.5;
      text-align:center;
    }

    /* Print tweaks */
    @media print{
      body{ background:#fff; }
      .sheet{ margin:0; box-shadow:none; }
    }
  </style>
</head>

<body>
  <main class="sheet">
    <!-- Black banner -->
    <header class="banner">
      <div class="brand">
        <div class="name">LEVITA</div>
        <div class="tag">Digital Consulting</div>
      </div>
      <div class="doc-type">Invoice</div>
    </header>

    <div class="content">
      <!-- Address + invoice meta -->
      <section class="top">
        <div class="addr-box">
          <div class="to">{{client_name}}</div>
          {% for line in client_address_lines %}
          <div class="line">{{line}}</div>
          {% endfor %}
        </div>

        <div class="meta">
          <div class="meta-row">
            <div class="label">Invoice Date</div>
            <div class="value">{{invoice_date}}</div>
          </div>
          <div class="meta-row">
            <div class="label">Invoice Number</div>
            <div class="value">{{invoice_number}}</div>
          </div>

          <div class="meta-row ref">
            <div class="label">Your Reference</div>
            <div class="value">{{your_reference}}</div>
          </div>
        </div>
      </section>

      <!-- Services -->
      <div class="section-head">
        <div>Description of Services</div>
        <div class="right">Ttl £</div>
      </div>

      <table class="services" aria-label="Services">
        {% for item in line_items %}
        <tr>
          <td class="desc">{{item.description}}</td>
          <td class="amt">£{{ "{:,.2f}".format(item.amount) }}</td>
        </tr>
        {% endfor %}
      </table>

      <!-- Payment terms + totals -->
      <section class="bottom">
        <div class="terms">
          <div class="due">Payments due in {{payment_terms_days}} days from Invoice Date</div>

          <div class="bank">
            <div style="margin-bottom:8mm;">Make Payments in GBP to :</div>

            <div><strong>{{payee_name}}</strong></div>
            <div><span class="label">Sort Code</span> <strong>{{sort_code}}</strong></div>
            <div><span class="label">Account Number</span> <strong>{{account_number}}</strong></div>

            <div style="margin-top:8mm;"><strong>International Payments</strong></div>
            <div><span class="label">IBAN</span> {{iban}}</div>
            <div><span class="label">BIC</span> <strong>{{bic}}</strong></div>
          </div>
        </div>

        <div class="totals" aria-label="Totals">
          <div class="row">
            <div class="label">Net</div>
            <div class="value">£{{ "{:,.2f}".format(net_total_gbp) }}</div>
          </div>
          {% if uk_vat %}
          <div class="row">
            <div class="label">VAT @ 20%</div>
            <div class="value">£{{ "{:,.2f}".format(vat_total_gbp) }}</div>
          </div>
          {% endif %}
          <div class="row total">
            <div class="label">Total Payable</div>
            <div class="value">£{{ "{:,.2f}".format(gross_total_gbp) }}</div>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="footer">
        Levita Consulting Ltd, UK Company number: 12345678
        VAT Registration Number GB 123 4567 89<br/>
        Contact +44 (0) 20 7123 4567 finance@levita.co.uk
        Registered office: 123 Levita Way, London, EC1A 1BB
      </footer>
    </div>
  </main>
</body>
</html>
"""

import os

# Create the directory if it doesn't exist
template_dir = "invoice templates"
if not os.path.exists(template_dir):
    os.makedirs(template_dir)

# Save the template to a file
template_filename = "default.html"
template_path = os.path.join(template_dir, template_filename)
with open(template_path, "w") as f:
    f.write(html)

conn = sqlite3.connect('timesheets.db')
c = conn.cursor()

# Ensure there is a settings row, then update the invoice_template_file
c.execute("SELECT id FROM settings LIMIT 1")
row = c.fetchone()
if row is None:
    c.execute(
        """
        INSERT INTO settings (draft_invoice_email, email_invoice_template, invoice_template_file, invoice_generation_timing, batch_submission_time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (None, None, template_filename, 'Immediate', None)
    )
else:
    c.execute("UPDATE settings SET invoice_template_file = ? WHERE id = ?", (template_filename, row[0]))

conn.commit()
conn.close()

print(f"Invoice template saved to {template_path} and settings updated in database.")
