import requests
from bs4 import BeautifulSoup
import boto3
import os

def scrape_and_send_email():
    # URL of the waiver wire rankings
    URL = "https://www.fantasypros.com/nfl/rankings/waiver-wire-half-point-ppr-overall.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        # Step 1: Fetch and parse the webpage
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Step 2: Extract the table
        table = soup.find("table", {"class": "table"})
        if not table:
            raise ValueError("Table not found on the page.")

        # Extract headers and rows
        headers = [th.text.strip() for th in table.find_all("th")]
        rows = [
            [td.text.strip() for td in tr.find_all("td")]
            for tr in table.find("tbody").find_all("tr")
        ]

        # Find indices of columns we need
        own_index = headers.index("OWN")
        pos_index = headers.index("POS")

        # Step 3: Filter data
        filtered_rows = [
            row for row in rows
            if float(row[own_index].replace('%', '')) < 45  # Filter "OWN" below 45%
            and not row[pos_index].startswith("K")          # Exclude "POS" starting with "K"
            and not row[pos_index].startswith("DST")        # Exclude "POS" starting with "DST"
        ]

        # Keep the top 5 rows
        filtered_rows = filtered_rows[:5]

        # Step 4: Create CSV content
        csv_content = ",".join(headers) + "\n"
        csv_content += "\n".join([",".join(row) for row in filtered_rows])

        # Step 5: Send the email using SES
        ses_client = boto3.client('ses', region_name='us-east-1')  # Adjust the region if necessary
        ses_client.send_email(
            Source=os.environ['EMAIL_SENDER'],  # Configure in Lambda environment
            Destination={
                'ToAddresses': [os.environ['EMAIL_RECEIVER']]
            },
            Message={
                'Subject': {'Data': 'Weekly Filtered Waiver Wire Rankings'},
                'Body': {
                    'Text': {'Data': f"Here are the top waiver wire rankings based on your criteria:\n\n{csv_content}"}
                }
            }
        )

        print("Email sent successfully.")

    except Exception as e:
        print(f"Error: {e}")

# Lambda handler
def lambda_handler(event, context):
    scrape_and_send_email()
