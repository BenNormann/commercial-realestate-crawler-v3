import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class EmailSender:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    def send_email(self, to_email, subject, body, email, password):
        """
        Send an email with the provided credentials and content
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            body (str): Email body text
            email (str): Sender email address
            password (str): Sender email password
        
        Returns:
            bool: Success status
        """
        # Create message
        message = MIMEMultipart()
        message["From"] = email
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add body to email
        message.attach(MIMEText(body, "plain"))
        
        try:
            # Connect to server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            # Login and send email
            server.login(email, password)
            server.sendmail(email, to_email, message.as_string())
            
            # Close connection
            server.quit()
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            raise e 