import json
from scanner.engine import run_scan
from scanner.report import format_report
from reporter.generator import generate_pdf


# Run the scan
raw = run_scan(
    target_url="https://httpbin.org/get",
    verbose=True,
    suggest_fix=False
)
# Format the report
report = format_report(raw)

# Print JSON to terminal
print(json.dumps(report, indent=2))

# Generate PDF
output = generate_pdf(report, output_path="shovl_report.pdf")
print(f"\nPDF generated: {output}")