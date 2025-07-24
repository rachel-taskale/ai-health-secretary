import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_confirmation_email_html(session_state:dict):
    session_state["name"].split(" ")
    formatted_start_time = session_state["start"].strftime("%B %d, %Y at %I:%M %p")
    formatted_end_time = session_state["start"].strftime("%B %d, %Y at %I:%M %p")
    latest_appointment_scheduled =session_state["schedule_appointment"][len(session_state["schedule_appointment"])-1]
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
                                Hi {session_state["name"]},<br><br>
                                This is a quick note to confirm your upcoming appointment with Dr.{latest_appointment_scheduled["doctor_name"]}:
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
        from_email='clinic@example.com',
        to_emails=session_state["email"],
        subject='Your Appointment with {} is Confirmed!',
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(f"Email sent: {response.status_code}")
    except Exception as e:
        print(f"Email failed: {e}")

