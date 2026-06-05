"""Live HTTP test - POSTs a real multipart form to /apply endpoint."""
import urllib.request, json

def encode_multipart(fields, files):
    boundary = b"----boundary12345"
    body = b""
    for name, value in fields.items():
        body += b"--" + boundary + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += value.encode() + b"\r\n"
    for name, (filename, content, ctype) in files.items():
        body += b"--" + boundary + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {ctype}\r\n\r\n".encode()
        body += content + b"\r\n"
    body += b"--" + boundary + b"--\r\n"
    return body, "multipart/form-data; boundary=----boundary12345"

fields = {
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "phone": "9876543210",
    "city": "Chennai",
    "college": "Test University",
    "department": "Computer Science",
    "year_of_study": "2nd Year",
    "passed_out_year": "N/A",
    "internship_domain": "Python Development",
    "fee_payment": "Yes",
    "notes": "automated test",
}

pdf_bytes = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n9\n%%EOF"
)

body, ctype = encode_multipart(fields, {"file": ("test_resume.pdf", pdf_bytes, "application/pdf")})

req = urllib.request.Request("http://localhost:8000/apply", data=body, method="POST")
req.add_header("Content-Type", ctype)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        print("HTTP Status:", resp.status)
        print("Response:", json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.read().decode())
except Exception as e:
    print("Error:", e)
