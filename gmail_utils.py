import os
import base64
import json
import pickle
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from jinja2 import Template

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

def get_gmail_service(credentials_json):
    if not credentials_json:
        return None
    
    try:
        creds_data = json.loads(credentials_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return None
        
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        print(f"Error getting Gmail service: {e}")
        return None

def get_user_signature(service, email_address):
    """Fetches the user's Gmail signature for a specific email address."""
    try:
        print(f"DEBUG: Fetching signature for {email_address}")
        results = service.users().settings().sendAs().list(userId='me').execute()
        send_as_configs = results.get('sendAs', [])
        
        for config in send_as_configs:
            if config.get('sendAsEmail') == email_address:
                signature = config.get('signature', '')
                if signature:
                    print(f"DEBUG: Found signature for {email_address}")
                    return signature
                break
        
        # If not found for specific email, try the primary one
        for config in send_as_configs:
            if config.get('isDefault'):
                signature = config.get('signature', '')
                if signature:
                    print(f"DEBUG: Found default signature")
                    return signature
        
        print(f"DEBUG: No signature found for {email_address}")
        return ""
    except Exception as e:
        print(f"DEBUG: Error fetching signature: {e}")
        return ""

def create_draft_with_attachment(service, sender, recipient, subject, body_text, attachment_path):
    try:
        print(f"DEBUG: Preparing draft for recipient: {recipient}")
        # Use comma instead of semicolon for multiple recipients
        if recipient:
            recipient = recipient.replace(';', ',')
            # Strip whitespace around commas to ensure clean recipient list
            recipient = ', '.join([r.strip() for r in recipient.split(',') if r.strip()])
            
        message = MIMEMultipart()
        message['to'] = recipient
        # Use provided sender address (e.g., alex@levita.co.uk)
        if sender:
            message['from'] = sender
        message['subject'] = subject

        # Fetch and append signature
        signature = get_user_signature(service, sender)
        
        # Determine if we should use HTML or plain text
        # If body_text is plain but signature has HTML tags, we might want to wrap it.
        # For now, let's keep it simple: if signature exists, append it.
        if signature:
            # Check if signature looks like HTML
            if '<' in signature and '>' in signature:
                # If we have an HTML signature, we should ideally send an HTML email.
                # Let's convert plain text body to simple HTML if we have an HTML signature.
                html_body = body_text.replace('\n', '<br>') + '<br><br>' + signature
                msg = MIMEText(html_body, 'html')
            else:
                full_body = body_text + "\n\n" + signature
                msg = MIMEText(full_body)
        else:
            msg = MIMEText(body_text)
            
        message.attach(msg)

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read(), _subtype="pdf")
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'message': {'raw': raw_message}}
        
        print(f"DEBUG: Calling Gmail API to create draft for {recipient}")
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        print(f"DEBUG: Gmail API response: {draft}")
        print(f'Draft id: {draft["id"]} created.')
        return draft
    except HttpError as error:
        print(f'An error occurred calling Gmail API: {error}')
        if error.resp.status == 403:
            print("DEBUG: Access forbidden. Check if Gmail API is enabled and scopes are correct.")
        return None
    except Exception as e:
        print(f"DEBUG: General error in create_draft_with_attachment: {e}")
        return None

def prepare_email_body(template_str, project, invoice_number, invoice_date, net_total, vat_total, gross_total):
    try:
        context = {
            'client_name': project.client_name,
            'project_name': project.name,
            'invoice_number': invoice_number,
            'invoice_date': invoice_date,
            'net_total': f"£{net_total:,.2f}",
            'vat_total': f"£{vat_total:,.2f}",
            'gross_total': f"£{gross_total:,.2f}",
            'amount': f"£{gross_total:,.2f}", # Alias for gross_total
            'client_ref': project.client_ref or "",
            'contact_name': project.key_contact or project.client_name
        }
        return Template(template_str).render(**context)
    except Exception as e:
        print(f"Error rendering email template: {e}")
        return template_str
