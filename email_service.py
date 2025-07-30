from datetime import datetime
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_confirmation_email_html(session_state:dict):
    print(session_state['appointments'])
    start_dt = datetime.fromisoformat(session_state['appointments']['start'])
    end_dt = datetime.fromisoformat(session_state['appointments']['end'])
    formatted_start_time = start_dt.strftime("%B %d, %Y at %I:%M %p")
    formatted_end_time = end_dt.strftime("%B %d, %Y at %I:%M %p")
    latest_appointment_scheduled =session_state['appointments']
    html_content = f"""
                        <html>
                        <head>
                            <style>
                            body {{
                                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                                background-color: #f9fafb;
                                padding: 40px;
                                color: #333;
                            }}
                            .container {{
                                max-width: 600px;
                                margin: auto;
                                background-color: #ffffff;
                                border-radius: 8px;
                                padding: 30px;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                            }}
                            .header {{
                                text-align: center;
                                padding-bottom: 20px;
                                color: #22c55e;
                            }}
                            .details {{
                                font-size: 16px;
                                line-height: 1.6;
                            }}
                            .footer {{
                                margin-top: 30px;
                                font-size: 14px;
                                color: #999;
                                text-align: center;
                            }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                            <h2 class="header">Appointment Confirmed</h2>
                            <p class="details">
                                Hi {session_state['name']['first_name'].capitalize()} {session_state['name']['last_name'].capitalize()},<br><br>
                                This is a quick note to confirm your upcoming appointment with Dr. {latest_appointment_scheduled['doctor_name'].capitalize()}:
                            </p>
                            <p class="details">
                                <strong>📅 Time:</strong> {formatted_start_time} until {formatted_end_time} <br>
                                <strong>📍 Location:</strong> 123 Wellness Blvd, San Francisco, CA
                            </p>
                            <p class="details">
                                If you have any questions or need to reschedule, feel free to reply to this email.
                            </p>
                            <p class="details">
                                Looking forward to seeing you!
                            </p>
                            </div>
                        </body>
                        </html>
                        """

    message = Mail(
        from_email='racheltaskale@gmail.com',
        to_emails=session_state["email"],
        subject=f"Your Appointment with Dr. {latest_appointment_scheduled['doctor_name'].capitalize()} is Confirmed!",
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(f"Email sent: {response.status_code}")
    except Exception as e:
        print(f"Email failed: {e}")

